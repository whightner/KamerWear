"""Return requests: eligibility, creation, the state machine and restocking.

Policy (documented in docs/architecture/returns-support.md):
- Only delivered orders, within RETURN_WINDOW_DAYS of the delivery recorded in
  the order's status history (not the order date).
- Per order line, at most the purchased quantity minus what is already in
  requests that are not rejected or cancelled.
- Value = purchase-time unit price x quantity (merchandise only, no delivery fee).
- Inventory never changes when a return is requested or approved. When staff
  mark it received they choose per line whether the units go back on sale
  (inventory.on_hand += quantity); `reserved` is never touched.
- Refunds are demo/manual records: no payment provider is contacted.

Every state change locks the return row first, so a repeated or simultaneous
request sees the new status and is rejected: stock is restocked and refunds
are recorded exactly once.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import RETURN_WINDOW_DAYS
from app.models import (
    Inventory,
    Order,
    OrderStatus,
    PaymentStatus,
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnStatus,
    ReturnStatusHistory,
    User,
    UserProfile,
)
from app.services import orders as order_service
from app.services.errors import ServiceError, not_found

_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

REASON_LABELS = {
    ReturnReason.wrong_size: "Wrong size",
    ReturnReason.damaged: "Item damaged",
    ReturnReason.wrong_item: "Wrong item",
    ReturnReason.not_as_expected: "Not as expected",
    ReturnReason.changed_mind: "Changed mind",
    ReturnReason.other: "Other",
}

# Requests that still count against the purchased quantity.
ACTIVE = (
    ReturnStatus.requested,
    ReturnStatus.approved,
    ReturnStatus.received,
    ReturnStatus.refunded,
)
FINAL = (ReturnStatus.rejected, ReturnStatus.refunded, ReturnStatus.cancelled)

# Staff actions and the status each one needs / leads to. Customers can only
# cancel, and only while the request is still `requested`.
TRANSITIONS: dict[ReturnStatus, tuple[ReturnStatus, ...]] = {
    ReturnStatus.requested: (ReturnStatus.approved, ReturnStatus.rejected, ReturnStatus.cancelled),
    ReturnStatus.approved: (ReturnStatus.received,),
    ReturnStatus.received: (ReturnStatus.refunded,),
    ReturnStatus.rejected: (),
    ReturnStatus.refunded: (),
    ReturnStatus.cancelled: (),
}
ACTIONS = {
    "approve": ReturnStatus.approved,
    "reject": ReturnStatus.rejected,
    "receive": ReturnStatus.received,
    "refund": ReturnStatus.refunded,
}

REFUND_NOTE = (
    "Demo/manual refund recorded. No payment-provider refund was executed "
    "(no Mobile Money, Orange Money or card refund)."
)


def return_not_found() -> ServiceError:
    # Same answer for "doesn't exist" and "belongs to someone else".
    return not_found("return_not_found", "We couldn't find a return with this reference.")


def new_return_number(db: Session) -> str:
    year = datetime.now().year
    while True:
        number = f"KR-{year}-{''.join(secrets.choice(_ALPHABET) for _ in range(6))}"
        if db.scalar(select(ReturnRequest.id).where(ReturnRequest.return_number == number)) is None:
            return number


def delivered_at(order: Order) -> datetime | None:
    """When the order was delivered, from its status history."""
    times = [e.created_at for e in order.status_history if e.status == OrderStatus.delivered]
    return max(times) if times else None


def returned_quantities(db: Session, order_id: int) -> dict[int, int]:
    """order_item_id -> quantity already in active requests for this order."""
    rows = db.execute(
        select(ReturnItem.order_item_id, func.sum(ReturnItem.quantity))
        .join(ReturnRequest, ReturnRequest.id == ReturnItem.return_request_id)
        .where(ReturnRequest.order_id == order_id, ReturnRequest.status.in_(ACTIVE))
        .group_by(ReturnItem.order_item_id)
    ).all()
    return {item_id: int(total) for item_id, total in rows}


@dataclass
class Eligibility:
    order: Order
    eligible: bool
    code: str | None
    message: str | None
    delivered_at: datetime | None
    deadline: datetime | None
    returned: dict[int, int]
    returns: list[ReturnRequest]


def _now() -> datetime:
    return datetime.now(UTC)


def check_eligibility(db: Session, order: Order, now: datetime | None = None) -> Eligibility:
    now = now or _now()
    delivered = delivered_at(order)
    deadline = delivered + timedelta(days=RETURN_WINDOW_DAYS) if delivered else None
    returned = returned_quantities(db, order.id)
    returns = db.scalars(
        select(ReturnRequest)
        .where(ReturnRequest.order_id == order.id)
        .order_by(ReturnRequest.created_at.desc(), ReturnRequest.id.desc())
    ).all()
    code = message = None
    if order.status != OrderStatus.delivered or delivered is None:
        code = "return_not_eligible"
        message = "Returns are possible once an order has been delivered."
    elif now > deadline:
        code = "return_window_expired"
        message = (
            f"The {RETURN_WINDOW_DAYS}-day return window for this order ended on "
            f"{deadline:%d %B %Y}."
        )
    elif all(returned.get(item.id, 0) >= item.quantity for item in order.items):
        code = "return_quantity_exceeded"
        message = "Every item of this order is already in a return request."
    return Eligibility(
        order=order,
        eligible=code is None,
        code=code,
        message=message,
        delivered_at=delivered,
        deadline=deadline,
        returned=returned,
        returns=list(returns),
    )


def eligibility_for(db: Session, user: User, order_number: str) -> Eligibility:
    return check_eligibility(db, order_service.get_order(db, user, order_number))


@dataclass
class NewItem:
    order_item_id: int
    quantity: int
    reason: ReturnReason
    note: str | None


def create_return(
    db: Session,
    user: User,
    order_number: str,
    items: list[NewItem],
    customer_note: str | None,
) -> ReturnRequest:
    """Validates everything against the customer's own order and creates the request."""
    order = db.scalar(
        select(Order)
        .where(Order.order_number == order_number.strip().upper(), Order.user_id == user.id)
        .with_for_update()  # serialises concurrent requests for the same order
    )
    if order is None:
        raise order_service.order_not_found()
    db.refresh(order, attribute_names=["items", "status_history"])
    check = check_eligibility(db, order)
    if not check.eligible:
        status = 422 if check.code == "return_quantity_exceeded" else 409
        raise ServiceError(status, check.code, check.message)

    by_id = {item.id: item for item in order.items}
    seen: set[int] = set()
    for item in items:
        if item.order_item_id not in by_id:
            raise ServiceError(
                422, "return_item_invalid", "One of the items isn't part of this order."
            )
        if item.order_item_id in seen:
            raise ServiceError(422, "return_item_invalid", "Each item can only be listed once.")
        seen.add(item.order_item_id)
        line = by_id[item.order_item_id]
        allowed = line.quantity - check.returned.get(line.id, 0)
        if item.quantity > allowed:
            raise ServiceError(
                422,
                "return_quantity_exceeded",
                f"You can return at most {allowed} of {line.product_name}"
                f"{f' ({line.size})' if line.size else ''}.",
                order_item_id=line.id,
                max_quantity=allowed,
            )

    reasons = list(dict.fromkeys(REASON_LABELS[item.reason] for item in items))
    request = ReturnRequest(
        return_number=new_return_number(db),
        user_id=user.id,
        order_id=order.id,
        status=ReturnStatus.requested,
        reason_summary=", ".join(reasons)[:120],
        customer_note=customer_note or None,
        return_value=sum(by_id[i.order_item_id].unit_price * i.quantity for i in items),
        items=[
            ReturnItem(
                order_item_id=i.order_item_id,
                quantity=i.quantity,
                reason=i.reason,
                condition_note=i.note or None,
            )
            for i in items
        ],
        status_history=[ReturnStatusHistory(status=ReturnStatus.requested, actor_user_id=user.id)],
    )
    db.add(request)
    db.flush()
    return request


def _with_details(query):
    return query.options(
        selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
        selectinload(ReturnRequest.status_history),
    )


def list_returns(
    db: Session, user: User, limit: int, offset: int
) -> tuple[list[tuple[ReturnRequest, str]], int]:
    """The customer's returns with their order numbers, newest first."""
    total = (
        db.scalar(select(func.count(ReturnRequest.id)).where(ReturnRequest.user_id == user.id)) or 0
    )
    rows = db.execute(
        select(ReturnRequest, Order.order_number)
        .join(Order, Order.id == ReturnRequest.order_id)
        .where(ReturnRequest.user_id == user.id)
        .options(selectinload(ReturnRequest.items))
        .order_by(ReturnRequest.created_at.desc(), ReturnRequest.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [(r, n) for r, n in rows], total


def get_return(db: Session, user: User, return_number: str) -> ReturnRequest:
    request = db.scalar(
        _with_details(select(ReturnRequest)).where(
            ReturnRequest.return_number == return_number.strip().upper(),
            ReturnRequest.user_id == user.id,
        )
    )
    if request is None:
        raise return_not_found()
    return request


def get_any_return(db: Session, return_number: str) -> ReturnRequest:
    request = db.scalar(
        _with_details(select(ReturnRequest))
        .where(ReturnRequest.return_number == return_number.strip().upper())
        .execution_options(populate_existing=True)
    )
    if request is None:
        raise return_not_found()
    return request


# --- State changes ---------------------------------------------------------------


def _move(
    db: Session,
    request: ReturnRequest,
    status: ReturnStatus,
    actor: User,
    note: str | None,
    internal_note: str | None = None,
) -> None:
    """Locks the row, checks the transition and records it."""
    db.refresh(request, with_for_update=True)
    if status not in TRANSITIONS[request.status]:
        allowed = ", ".join(s.value for s in TRANSITIONS[request.status]) or "none"
        raise ServiceError(
            409,
            "invalid_return_transition",
            f"Return {request.return_number} can't go from {request.status.value} to "
            f"{status.value}. Allowed next statuses: {allowed}.",
        )
    request.status = status
    if status in FINAL:
        request.resolved_at = _now()
    request.status_history.append(
        ReturnStatusHistory(
            status=status,
            actor_user_id=actor.id,
            customer_note=note or None,
            internal_note=internal_note or None,
        )
    )


def cancel(db: Session, user: User, request: ReturnRequest, note: str | None) -> None:
    """The customer withdraws a request the store hasn't acted on yet."""
    db.refresh(request, with_for_update=True)
    if request.status != ReturnStatus.requested:
        raise ServiceError(
            409,
            "invalid_return_transition",
            "This return can no longer be cancelled: the store has already handled it.",
        )
    _move(db, request, ReturnStatus.cancelled, user, note)
    db.flush()


def approve(db, request, admin, note=None, internal_note=None) -> None:
    _move(db, request, ReturnStatus.approved, admin, note, internal_note)
    db.flush()


def reject(db, request, admin, note=None, internal_note=None) -> None:
    _move(db, request, ReturnStatus.rejected, admin, note, internal_note)
    db.flush()


def receive(
    db: Session,
    request: ReturnRequest,
    admin: User,
    restock: dict[int, bool],
    note: str | None = None,
    internal_note: str | None = None,
) -> None:
    """Marks the parcel received and puts restockable units back on sale, once."""
    _move(db, request, ReturnStatus.received, admin, note, internal_note)
    item_ids = {item.id for item in request.items}
    if set(restock) != item_ids:
        raise ServiceError(
            422,
            "restock_decision_required",
            "Choose 'restockable' or 'not restockable' for every returned item.",
        )
    to_restock = [item for item in request.items if restock[item.id]]
    variant_ids = sorted({i.order_item.variant_id for i in to_restock if i.order_item.variant_id})
    rows = db.scalars(
        select(Inventory)
        .where(Inventory.variant_id.in_(variant_ids))
        .order_by(Inventory.variant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    by_variant = {row.variant_id: row for row in rows}
    for item in request.items:
        item.restock = restock[item.id]
        if not item.restock:
            continue
        row = by_variant.get(item.order_item.variant_id)
        if row is None:
            raise ServiceError(
                409,
                "return_item_not_restockable",
                f"{item.order_item.product_name} ({item.order_item.sku}) no longer exists in "
                "the catalog; mark it as not restockable.",
            )
        row.on_hand += item.quantity  # `reserved` is never touched for delivered orders
    db.flush()


def fully_refunded_after(db: Session, request: ReturnRequest, order: Order) -> bool:
    """True if refunded returns (including this one) cover every unit of the order."""
    rows = db.execute(
        select(ReturnItem.order_item_id, func.sum(ReturnItem.quantity))
        .join(ReturnRequest, ReturnRequest.id == ReturnItem.return_request_id)
        .where(
            ReturnRequest.order_id == order.id,
            or_(
                ReturnRequest.status == ReturnStatus.refunded,
                ReturnRequest.id == request.id,
            ),
        )
        .group_by(ReturnItem.order_item_id)
    ).all()
    covered = {item_id: int(total) for item_id, total in rows}
    return all(covered.get(item.id, 0) >= item.quantity for item in order.items)


def can_mark_order_refunded(db: Session, request: ReturnRequest, order: Order) -> bool:
    return (
        request.status == ReturnStatus.received
        and order.payment_status == PaymentStatus.paid
        and fully_refunded_after(db, request, order)
    )


def refund(
    db: Session,
    request: ReturnRequest,
    admin: User,
    note: str | None = None,
    internal_note: str | None = None,
    *,
    mark_order_payment_refunded: bool = False,
) -> None:
    """Records the demo/manual refund of the merchandise value. No money moves."""
    _move(db, request, ReturnStatus.refunded, admin, note, internal_note)
    request.refunded_amount = request.return_value
    if mark_order_payment_refunded:
        order = db.get(Order, request.order_id)
        if order.payment_status != PaymentStatus.paid:
            raise ServiceError(
                409,
                "order_payment_not_paid",
                "The order payment isn't marked paid, so it can't be marked refunded.",
            )
        if not fully_refunded_after(db, request, order):
            raise ServiceError(
                409,
                "order_not_fully_returned",
                "Only mark the whole order payment refunded when every item has been returned.",
            )
        order_service.change_payment_status(
            db,
            order,
            PaymentStatus.refunded,
            f"Demo refund recorded for return {request.return_number}.",
            changed_by=admin,
        )
    db.flush()


def allowed_actions(request: ReturnRequest) -> list[str]:
    nexts = TRANSITIONS[request.status]
    return [name for name, status in ACTIONS.items() if status in nexts]


# --- Admin list --------------------------------------------------------------------


def admin_list(
    db: Session,
    *,
    q: str | None,
    status: ReturnStatus | None,
    date_from,
    date_to,
    limit: int,
    offset: int,
) -> tuple[list[tuple[ReturnRequest, str, User]], int]:
    query = (
        select(ReturnRequest, Order.order_number, User)
        .join(Order, Order.id == ReturnRequest.order_id)
        .join(User, User.id == ReturnRequest.user_id)
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.outerjoin(UserProfile, UserProfile.user_id == User.id).where(
            or_(
                ReturnRequest.return_number.ilike(pattern),
                Order.order_number.ilike(pattern),
                User.email.ilike(pattern),
                (UserProfile.first_name + " " + UserProfile.last_name).ilike(pattern),
            )
        )
    if status is not None:
        query = query.where(ReturnRequest.status == status)
    if date_from is not None:
        query = query.where(cast(ReturnRequest.created_at, Date) >= date_from)
    if date_to is not None:
        query = query.where(cast(ReturnRequest.created_at, Date) <= date_to)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.options(selectinload(ReturnRequest.items), joinedload(User.profile))
        .order_by(ReturnRequest.created_at.desc(), ReturnRequest.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [(r, n, u) for r, n, u in rows], total


def requested_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count(ReturnRequest.id)).where(
                ReturnRequest.status.in_((ReturnStatus.requested, ReturnStatus.approved))
            )
        )
        or 0
    )
