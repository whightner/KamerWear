"""Admin inventory, order fulfilment and dashboard figures.

Inventory rule: staff set the physical stock (`on_hand`) only. `reserved` is
owned by orders (placing reserves, delivering or cancelling releases), so it
is read-only here, and on_hand may never drop below it.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import LOW_STOCK_THRESHOLD
from app.models import (
    Inventory,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    Product,
    ProductVariant,
    Role,
    User,
    UserProfile,
)
from app.schemas.admin_store import (
    AdminOrderDetail,
    AdminOrderSummary,
    AdminPaymentEvent,
    AdminStatusEvent,
    CustomerRef,
    InventoryProduct,
    InventoryRow,
    Overview,
    OverviewMetrics,
)
from app.schemas.orders import DeliveryAddressSnapshot, OrderItemResponse
from app.services import orders as order_service
from app.services.admin_catalog import stock_state
from app.services.errors import ServiceError

STORE_TIMEZONE = ZoneInfo("Africa/Douala")
AWAITING_ACTION = (OrderStatus.pending, OrderStatus.confirmed, OrderStatus.preparing)
IN_DELIVERY = (OrderStatus.shipped, OrderStatus.out_for_delivery)


# --- Inventory ---------------------------------------------------------------------


def _available():
    return func.greatest(Inventory.on_hand - Inventory.reserved, 0)


def _inventory_query():
    return (
        select(ProductVariant, Inventory, Product)
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(Inventory, Inventory.variant_id == ProductVariant.id)
    )


def _inventory_row(variant: ProductVariant, inventory: Inventory | None, product: Product):
    on_hand = inventory.on_hand if inventory else 0
    reserved = inventory.reserved if inventory else 0
    available = max(0, on_hand - reserved)
    return InventoryRow(
        variant_id=variant.id,
        sku=variant.sku,
        size=variant.size,
        color_name=variant.color_name,
        variant_active=variant.is_active,
        product=InventoryProduct(
            id=product.id, name=product.name, slug=product.slug, is_active=product.is_active
        ),
        on_hand=on_hand,
        reserved=reserved,
        available_quantity=available,
        stock_state=stock_state(available),
        updated_at=inventory.updated_at if inventory else None,
    )


def list_inventory(
    db: Session,
    *,
    q: str | None,
    product_id: int | None,
    low_stock: bool,
    out_of_stock: bool,
    include_inactive: bool,
    limit: int,
    offset: int,
) -> tuple[list[InventoryRow], int]:
    """Variants with stock. Low stock = 1..threshold available; out = 0 available."""
    available = func.coalesce(_available(), 0)
    query = _inventory_query()
    if not include_inactive:
        query = query.where(ProductVariant.is_active.is_(True), Product.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Product.name.ilike(pattern),
                ProductVariant.sku.ilike(pattern),
                ProductVariant.color_name.ilike(pattern),
            )
        )
    if product_id is not None:
        query = query.where(ProductVariant.product_id == product_id)
    if low_stock and out_of_stock:
        query = query.where(available <= LOW_STOCK_THRESHOLD)
    elif low_stock:
        query = query.where(available > 0, available <= LOW_STOCK_THRESHOLD)
    elif out_of_stock:
        query = query.where(available <= 0)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(available, Product.name, ProductVariant.sku).limit(limit).offset(offset)
    ).all()
    return [_inventory_row(*row) for row in rows], total


def inventory_row(db: Session, variant_id: int) -> InventoryRow:
    row = db.execute(_inventory_query().where(ProductVariant.id == variant_id)).first()
    if row is None:
        raise ServiceError(404, "variant_not_found", "This variant doesn't exist.")
    return _inventory_row(*row)


def set_on_hand(db: Session, variant_id: int, on_hand: int) -> None:
    """Sets physical stock. The row is locked so a checkout can't reserve in between."""
    inventory = db.scalar(
        select(Inventory)
        .where(Inventory.variant_id == variant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if inventory is None:
        if db.get(ProductVariant, variant_id) is None:
            raise ServiceError(404, "variant_not_found", "This variant doesn't exist.")
        inventory = Inventory(variant_id=variant_id, on_hand=0, reserved=0)
        db.add(inventory)
    if on_hand < inventory.reserved:
        noun = "unit is" if inventory.reserved == 1 else "units are"
        raise ServiceError(
            409,
            "inventory_below_reserved",
            f"Cannot set on-hand stock to {on_hand} because {inventory.reserved} {noun} "
            "reserved by orders.",
            reserved=inventory.reserved,
        )
    inventory.on_hand = on_hand
    db.flush()


# --- Orders --------------------------------------------------------------------------


def order_not_found() -> ServiceError:
    return ServiceError(404, "order_not_found", "There is no order with this number.")


def _customer(user: User) -> CustomerRef:
    profile = user.profile
    name = f"{profile.first_name} {profile.last_name}" if profile else user.email
    return CustomerRef(
        id=user.id, email=user.email, name=name, phone=profile.phone if profile else None
    )


def list_orders(
    db: Session,
    *,
    q: str | None,
    status: OrderStatus | None,
    payment_status: PaymentStatus | None,
    city: str | None,
    limit: int,
    offset: int,
) -> tuple[list[AdminOrderSummary], int]:
    """All customers' orders, newest first."""
    item_count = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .where(OrderItem.order_id == Order.id)
        .scalar_subquery()
    )
    query = select(Order, User, item_count).join(User, User.id == Order.user_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.outerjoin(UserProfile, UserProfile.user_id == User.id).where(
            or_(
                Order.order_number.ilike(pattern),
                User.email.ilike(pattern),
                (UserProfile.first_name + " " + UserProfile.last_name).ilike(pattern),
                Order.delivery_phone.ilike(pattern),
            )
        )
    if status is not None:
        query = query.where(Order.status == status)
    if payment_status is not None:
        query = query.where(Order.payment_status == payment_status)
    if city:
        query = query.where(func.lower(Order.delivery_city) == city.strip().lower())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.options(joinedload(User.profile))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [_summary(order, user, count) for order, user, count in rows], total


def _summary(order: Order, user: User, item_count: int) -> AdminOrderSummary:
    return AdminOrderSummary(
        order_number=order.order_number,
        created_at=order.created_at,
        customer=_customer(user),
        total=order.total,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        status=order.status,
        city=order.delivery_city,
        item_count=item_count,
    )


def get_order(db: Session, order_number: str) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.order_number == order_number.strip().upper())
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.payment_history),
        )
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise order_not_found()
    return order


def order_detail(db: Session, order: Order) -> AdminOrderDetail:
    user = db.scalar(select(User).where(User.id == order.user_id).options(joinedload(User.profile)))
    actor_ids = {e.changed_by_user_id for e in order.status_history if e.changed_by_user_id} | {
        e.changed_by_user_id for e in order.payment_history if e.changed_by_user_id
    }
    actors = (
        dict(db.execute(select(User.id, User.email).where(User.id.in_(actor_ids))).all())
        if actor_ids
        else {}
    )
    return AdminOrderDetail(
        **_summary(order, user, order.item_count).model_dump(),
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount_total=order.discount_total,
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
        items=[OrderItemResponse.model_validate(item) for item in order.items],
        status_history=[
            AdminStatusEvent(
                status=e.status,
                note=e.note,
                internal_note=e.internal_note,
                changed_by=actors.get(e.changed_by_user_id),
                created_at=e.created_at,
            )
            for e in order.status_history
        ],
        payment_history=[
            AdminPaymentEvent(
                from_status=e.from_status,
                to_status=e.to_status,
                note=e.note,
                changed_by=actors.get(e.changed_by_user_id),
                created_at=e.created_at,
            )
            for e in order.payment_history
        ],
        timeline=order_service.timeline(order),
        allowed_statuses=list(order_service.ORDER_TRANSITIONS[order.status]),
        allowed_payment_statuses=list(order_service.allowed_payment_statuses(order)),
    )


# --- Overview ------------------------------------------------------------------------


def overview(db: Session) -> Overview:
    """Dashboard figures, each computed with SQL aggregates."""
    available = func.coalesce(_available(), 0)
    sellable = (
        select(ProductVariant.id, available.label("available"))
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(Inventory, Inventory.variant_id == ProductVariant.id)
        .where(ProductVariant.is_active.is_(True), Product.is_active.is_(True))
        .subquery()
    )
    variant_stats = db.execute(
        select(
            func.count(sellable.c.id),
            func.count(sellable.c.id).filter(
                sellable.c.available > 0, sellable.c.available <= LOW_STOCK_THRESHOLD
            ),
            func.count(sellable.c.id).filter(sellable.c.available <= 0),
        )
    ).one()
    product_stats = db.execute(
        select(
            func.count(Product.id).filter(Product.is_active.is_(True)),
            func.count(Product.id).filter(Product.is_active.is_(False)),
        )
    ).one()
    start_of_today = datetime.combine(datetime.now(STORE_TIMEZONE).date(), time(), STORE_TIMEZONE)
    not_cancelled = Order.status != OrderStatus.cancelled
    order_stats = db.execute(
        select(
            func.count(Order.id).filter(Order.status.in_(AWAITING_ACTION)),
            func.count(Order.id).filter(Order.status.in_(IN_DELIVERY)),
            func.count(Order.id).filter(Order.created_at >= start_of_today),
            func.coalesce(func.sum(Order.total).filter(not_cancelled), 0),
            func.coalesce(
                func.sum(Order.total).filter(Order.payment_status == PaymentStatus.paid), 0
            ),
        )
    ).one()
    customers = db.scalar(select(func.count(User.id)).where(User.role == Role.customer)) or 0

    recent, _ = list_orders(
        db, q=None, status=None, payment_status=None, city=None, limit=5, offset=0
    )
    low_stock, _ = list_inventory(
        db,
        q=None,
        product_id=None,
        low_stock=True,
        out_of_stock=True,
        include_inactive=False,
        limit=8,
        offset=0,
    )
    return Overview(
        metrics=OverviewMetrics(
            active_products=product_stats[0],
            inactive_products=product_stats[1],
            active_variants=variant_stats[0],
            low_stock_variants=variant_stats[1],
            out_of_stock_variants=variant_stats[2],
            orders_awaiting_action=order_stats[0],
            orders_in_delivery=order_stats[1],
            orders_today=order_stats[2],
            customers=customers,
            order_value=int(order_stats[3]),
            paid_order_value=int(order_stats[4]),
            low_stock_threshold=LOW_STOCK_THRESHOLD,
        ),
        recent_orders=recent,
        low_stock=low_stock,
    )
