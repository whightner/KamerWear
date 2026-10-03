"""Checkout quote, order creation, order history and status tracking.

The server is the source of truth: prices come from the catalog, stock from
inventory and the delivery fee from services/delivery.py. Nothing about
money or stock is accepted from the client.

Inventory policy: placing an order reserves stock (inventory.reserved += qty),
so available = on_hand - reserved drops immediately. Delivering converts the
reservation (on_hand -= qty, reserved -= qty); cancelling releases it
(reserved -= qty). Stock is therefore never counted twice.
"""

import secrets
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Cart,
    Inventory,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    User,
)
from app.schemas.address import AddressResponse
from app.schemas.orders import (
    DEMO_PAYMENT_NOTES,
    DeliveryAddressSnapshot,
    OrderCreate,
    OrderDetail,
    QuoteResponse,
    TimelineStep,
)
from app.services import addresses as address_service
from app.services import cart as cart_service
from app.services.delivery import delivery_fee
from app.services.errors import ServiceError, not_found

# Unambiguous characters (no 0/O, 1/I/L) for order references like KW-2026-7K4M9Q.
_ORDER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

TIMELINE = (
    (OrderStatus.pending, "Order placed"),
    (OrderStatus.confirmed, "Confirmed"),
    (OrderStatus.preparing, "Preparing"),
    (OrderStatus.shipped, "Shipped"),
    (OrderStatus.out_for_delivery, "Out for delivery"),
    (OrderStatus.delivered, "Delivered"),
)


def cart_empty() -> ServiceError:
    return ServiceError(400, "cart_empty", "Your cart is empty.")


def order_not_found() -> ServiceError:
    # Same answer for "doesn't exist" and "belongs to someone else".
    return not_found("order_not_found", "We couldn't find an order with this reference.")


def new_order_number(db: Session) -> str:
    """Random, non-sequential reference. The unique index is the final guard."""
    year = datetime.now().year
    while True:
        code = "".join(secrets.choice(_ORDER_ALPHABET) for _ in range(6))
        number = f"KW-{year}-{code}"
        if db.scalar(select(Order.id).where(Order.order_number == number)) is None:
            return number


def _totals(subtotal: int, fee: int | None) -> tuple[int, int]:
    """(discount_total, total). No promo codes yet: sale prices are already in
    the variant price, so the extra discount is 0."""
    discount = 0
    return discount, subtotal + (fee or 0) - discount


# --- Quote -------------------------------------------------------------------


def quote(
    db: Session,
    user: User,
    address_id: int | None,
    payment_method: PaymentMethod | None,
) -> QuoteResponse:
    cart = cart_service.read_cart(db, user)
    issues = [f"{line.product.name}: {line.issue}" for line in cart.items if line.issue]
    if not cart.items:
        issues.insert(0, "Your cart is empty.")

    address = None
    fee = None
    if address_id is not None:
        address = address_service.get_address(db, user, address_id)
        fee = delivery_fee(address.city)
    else:
        issues.append("Choose a delivery address.")
    if payment_method is None:
        issues.append("Choose a payment method.")

    discount, total = _totals(cart.subtotal, fee)
    return QuoteResponse(
        items=cart.items,
        item_count=cart.item_count,
        subtotal=cart.subtotal,
        delivery_fee=fee,
        discount_total=discount,
        total=total,
        address=AddressResponse.model_validate(address) if address else None,
        payment_method=payment_method,
        payment_note=DEMO_PAYMENT_NOTES[payment_method] if payment_method else None,
        issues=issues,
        can_place_order=not issues,
    )


# --- Order creation ------------------------------------------------------------


def _existing_order(db: Session, user: User, idempotency_key: str) -> Order | None:
    return db.scalar(
        select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key)
    )


def create_order(
    db: Session, user: User, data: OrderCreate, idempotency_key: str
) -> tuple[Order, bool]:
    """Places an order from the user's cart in the caller's transaction.

    Returns (order, created). Repeating a request with the same idempotency key
    returns the first order with created=False instead of ordering twice.
    The caller commits on success and rolls back on any error.
    """
    # 1. Serialise checkouts of the same customer: a double-click waits here
    #    until the first request commits, then finds its order below.
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id).with_for_update())
    existing = _existing_order(db, user, idempotency_key)
    if existing is not None:
        return existing, False
    if cart is None:
        raise cart_empty()

    address = address_service.get_address(db, user, data.address_id)

    # 2. Load the cart lines with current catalog data.
    cart = db.scalar(cart_service.cart_query(user).execution_options(populate_existing=True))
    items = list(cart.items)
    if not items:
        raise cart_empty()

    # 3. Lock the inventory rows (in a fixed order to avoid deadlocks) and
    #    re-read them, so two customers can't both buy the last unit: the second
    #    waits for the first to commit and then sees the reduced stock.
    variant_ids = sorted(item.variant_id for item in items)
    locked = db.scalars(
        select(Inventory)
        .where(Inventory.variant_id.in_(variant_ids))
        .order_by(Inventory.variant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    inventory_by_variant = {row.variant_id: row for row in locked}

    # 4. Re-validate every line against current stock.
    for item in items:
        variant = item.variant
        inventory = inventory_by_variant.get(variant.id)
        available = inventory.available if inventory else 0
        if not cart_service.is_sellable(variant):
            available = 0
        if item.quantity > available:
            raise cart_service.insufficient_stock(variant, available)

    # 5. Server-side prices and delivery fee.
    subtotal = sum(item.variant.price * item.quantity for item in items)
    fee = delivery_fee(address.city)
    discount, total = _totals(subtotal, fee)
    if data.expected_total is not None and data.expected_total != total:
        raise ServiceError(
            409,
            "quote_changed",
            "Prices or the delivery fee have changed. Please review the updated total.",
            total=total,
        )

    # 6–7. The order, with copies of the address and of each line.
    order = Order(
        order_number=new_order_number(db),
        user_id=user.id,
        idempotency_key=idempotency_key,
        status=OrderStatus.pending,
        payment_method=data.payment_method,
        subtotal=subtotal,
        delivery_fee=fee,
        discount_total=discount,
        total=total,
        delivery_label=address.label,
        delivery_recipient_name=address.recipient_name,
        delivery_phone=address.phone,
        delivery_country_code=address.country_code,
        delivery_region=address.region,
        delivery_city=address.city,
        delivery_quarter=address.quarter,
        delivery_landmark=address.street_or_landmark,
        delivery_latitude=address.latitude,
        delivery_longitude=address.longitude,
    )
    for item in items:
        variant = item.variant
        image = cart_service.image_for(variant)
        order.items.append(
            OrderItem(
                product_id=variant.product_id,
                variant_id=variant.id,
                product_name=variant.product.name,
                product_slug=variant.product.slug,
                sku=variant.sku,
                size=variant.size,
                color_name=variant.color_name,
                image_path=image.image_path if image else None,
                unit_price=variant.price,
                quantity=item.quantity,
                line_total=variant.price * item.quantity,
            )
        )
        # 8. Reserve the stock.
        inventory_by_variant[variant.id].reserved += item.quantity
    order.status_history.append(
        OrderStatusHistory(status=OrderStatus.pending, note="Order placed.")
    )
    db.add(order)

    # 9. Empty the cart (everything in it was ordered).
    cart.items.clear()
    db.flush()
    return order, True


# --- Reading orders ----------------------------------------------------------


def _with_details(query):
    return query.options(selectinload(Order.items), selectinload(Order.status_history))


def list_orders(db: Session, user: User, limit: int, offset: int) -> tuple[list[Order], int]:
    """The user's orders, newest first."""
    total = db.scalar(select(func.count(Order.id)).where(Order.user_id == user.id)) or 0
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(orders), total


def get_order(db: Session, user: User, order_number: str) -> Order:
    order = db.scalar(
        _with_details(select(Order)).where(
            Order.order_number == order_number.strip().upper(), Order.user_id == user.id
        )
    )
    if order is None:
        raise order_not_found()
    return order


def timeline(order: Order) -> list[TimelineStep]:
    """The fixed delivery steps, marked done/current/upcoming from the status.

    A cancelled order shows the steps it reached as done and nothing as current.
    """
    reached_at = {}
    for event in order.status_history:
        reached_at.setdefault(event.status, event.created_at)
    statuses = [status for status, _ in TIMELINE]
    if order.status == OrderStatus.cancelled:
        reached = [s for s in statuses if s in reached_at]
        current_index = statuses.index(reached[-1]) if reached else 0
    else:
        current_index = statuses.index(order.status)

    steps = []
    for index, (status, label) in enumerate(TIMELINE):
        if index < current_index or (
            order.status == OrderStatus.cancelled and index == current_index
        ):
            state = "done"
        elif index == current_index:
            state = "done" if status == OrderStatus.delivered else "current"
        else:
            state = "upcoming"
        steps.append(
            TimelineStep(
                status=status,
                label=label,
                state=state,
                reached_at=reached_at.get(status) if state != "upcoming" else None,
            )
        )
    return steps


def order_detail(order: Order) -> OrderDetail:
    return OrderDetail(
        order_number=order.order_number,
        created_at=order.created_at,
        status=order.status,
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        total=order.total,
        item_count=order.item_count,
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount_total=order.discount_total,
        payment_note=DEMO_PAYMENT_NOTES[order.payment_method],
        delivery=DeliveryAddressSnapshot(
            label=order.delivery_label,
            recipient_name=order.delivery_recipient_name,
            phone=order.delivery_phone,
            country_code=order.delivery_country_code,
            region=order.delivery_region,
            city=order.delivery_city,
            quarter=order.delivery_quarter,
            landmark=order.delivery_landmark,
            latitude=order.delivery_latitude,
            longitude=order.delivery_longitude,
        ),
        items=order.items,
        status_history=order.status_history,
        timeline=timeline(order),
        is_cancelled=order.status == OrderStatus.cancelled,
    )


# --- Status changes (setup tooling; no admin dashboard yet) ------------------


def change_status(db: Session, order: Order, status: OrderStatus, note: str | None) -> None:
    """Moves an order to a new status and keeps inventory consistent.

    delivered: the reserved units leave the warehouse (on_hand and reserved drop).
    cancelled: the reservation is released (reserved drops).
    """
    if order.status in (OrderStatus.delivered, OrderStatus.cancelled):
        raise ServiceError(
            409,
            "order_closed",
            f"Order {order.order_number} is already {order.status.value}.",
        )
    if status == order.status:
        return
    if status in (OrderStatus.delivered, OrderStatus.cancelled):
        variant_ids = [item.variant_id for item in order.items if item.variant_id is not None]
        rows = db.scalars(
            select(Inventory)
            .where(Inventory.variant_id.in_(variant_ids))
            .order_by(Inventory.variant_id)
            .with_for_update()
        ).all()
        by_variant = {row.variant_id: row for row in rows}
        for item in order.items:
            row = by_variant.get(item.variant_id)
            if row is None:
                continue
            row.reserved = max(0, row.reserved - item.quantity)
            if status == OrderStatus.delivered:
                row.on_hand = max(0, row.on_hand - item.quantity)
    order.status = status
    order.status_history.append(OrderStatusHistory(status=status, note=note))
    db.flush()
