"""Admin: store-wide returns and their processing (ADMIN only)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminUser, DbSession, require_admin
from app.api.v1.endpoints.returns import item_fields, refund_note, summary_fields
from app.models import Order, ReturnRequest, ReturnStatus, User
from app.schemas.catalog import ErrorResponse
from app.schemas.returns import (
    AdminReturnDetail,
    AdminReturnEvent,
    AdminReturnItem,
    AdminReturnList,
    AdminReturnOrder,
    AdminReturnSummary,
    ReturnDecision,
    ReturnReceive,
    ReturnRefund,
)
from app.services import admin_store
from app.services import returns as service

router = APIRouter(
    prefix="/admin/returns",
    tags=["admin: returns"],
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "authentication_required"},
        403: {"model": ErrorResponse, "description": "admin_required"},
        404: {"model": ErrorResponse, "description": "return_not_found"},
    },
)
TRANSITION_ERRORS = {409: {"model": ErrorResponse, "description": "invalid_return_transition"}}


def admin_detail(db, request: ReturnRequest) -> AdminReturnDetail:
    order = db.get(Order, request.order_id)
    db.refresh(order, attribute_names=["items", "status_history"])
    user = db.get(User, request.user_id)
    actor_ids = {e.actor_user_id for e in request.status_history if e.actor_user_id}
    actors = (
        {u.id: u.email for u in db.query(User).filter(User.id.in_(actor_ids))} if actor_ids else {}
    )
    return AdminReturnDetail(
        **summary_fields(request, order.order_number),
        customer=admin_store._customer(user),
        customer_note=request.customer_note,
        updated_at=request.updated_at,
        resolved_at=request.resolved_at,
        refunded_amount=request.refunded_amount,
        refund_note=refund_note(request),
        order=AdminReturnOrder(
            order_number=order.order_number,
            status=order.status,
            payment_status=order.payment_status,
            payment_method=order.payment_method,
            total=order.total,
            delivery_fee=order.delivery_fee,
            delivered_at=service.delivered_at(order),
        ),
        items=[
            AdminReturnItem(
                **item_fields(item),
                variant_id=item.order_item.variant_id,
                restock=item.restock,
            )
            for item in request.items
        ],
        history=[
            AdminReturnEvent(
                status=e.status,
                note=e.customer_note,
                internal_note=e.internal_note,
                changed_by=actors.get(e.actor_user_id),
                created_at=e.created_at,
            )
            for e in request.status_history
        ],
        allowed_actions=service.allowed_actions(request),
        can_mark_order_refunded=service.can_mark_order_refunded(db, request, order),
    )


@router.get("", summary="All return requests, newest first")
def list_returns(
    db: DbSession,
    q: Annotated[
        str | None, Query(max_length=100, description="Return number, order number, email, name")
    ] = None,
    status: ReturnStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminReturnList:
    rows, total = service.admin_list(
        db, q=q, status=status, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )
    return AdminReturnList(
        items=[
            AdminReturnSummary(**summary_fields(r, n), customer=admin_store._customer(u))
            for r, n, u in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{return_number}", summary="Any return, with internal history and next steps")
def read_return(return_number: str, db: DbSession) -> AdminReturnDetail:
    return admin_detail(db, service.get_any_return(db, return_number))


def _run(db, return_number: str, action) -> AdminReturnDetail:
    request = service.get_any_return(db, return_number)
    try:
        action(request)
    except Exception:
        db.rollback()
        raise
    db.commit()
    return admin_detail(db, service.get_any_return(db, return_number))


@router.post(
    "/{return_number}/approve", summary="Approve a requested return", responses=TRANSITION_ERRORS
)
def approve(
    return_number: str, data: ReturnDecision, admin: AdminUser, db: DbSession
) -> AdminReturnDetail:
    return _run(
        db, return_number, lambda r: service.approve(db, r, admin, data.note, data.internal_note)
    )


@router.post(
    "/{return_number}/reject", summary="Reject a requested return", responses=TRANSITION_ERRORS
)
def reject(
    return_number: str, data: ReturnDecision, admin: AdminUser, db: DbSession
) -> AdminReturnDetail:
    return _run(
        db, return_number, lambda r: service.reject(db, r, admin, data.note, data.internal_note)
    )


@router.post(
    "/{return_number}/receive",
    summary="Mark the returned items received, choosing which go back on sale",
    description="Restockable lines add their quantity to inventory.on_hand, exactly once. "
    "`reserved` is never changed.",
    responses={
        **TRANSITION_ERRORS,
        422: {"model": ErrorResponse, "description": "restock_decision_required"},
    },
)
def receive(
    return_number: str, data: ReturnReceive, admin: AdminUser, db: DbSession
) -> AdminReturnDetail:
    decisions = {item.return_item_id: item.restock for item in data.items}
    return _run(
        db,
        return_number,
        lambda r: service.receive(db, r, admin, decisions, data.note, data.internal_note),
    )


@router.post(
    "/{return_number}/refund",
    summary="Record the demo/manual refund",
    description="Records that the merchandise value was refunded outside the system. No "
    "payment provider is contacted and no money moves.",
    responses={
        409: {
            "model": ErrorResponse,
            "description": "invalid_return_transition / order_payment_not_paid / "
            "order_not_fully_returned",
        }
    },
)
def refund(
    return_number: str, data: ReturnRefund, admin: AdminUser, db: DbSession
) -> AdminReturnDetail:
    return _run(
        db,
        return_number,
        lambda r: service.refund(
            db,
            r,
            admin,
            data.note,
            data.internal_note,
            mark_order_payment_refunded=data.mark_order_payment_refunded,
        ),
    )
