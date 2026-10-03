"""Admin requests/responses for inventory, orders and the dashboard overview."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.orders import DeliveryAddressSnapshot, OrderItemResponse, TimelineStep

# --- Inventory ---------------------------------------------------------------------


class InventoryProduct(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool


class InventoryRow(BaseModel):
    variant_id: int
    sku: str
    size: str | None
    color_name: str
    variant_active: bool
    product: InventoryProduct
    on_hand: int
    # Held by placed orders; changed only by orders (placing, delivering, cancelling).
    reserved: int
    available_quantity: int
    stock_state: str  # "out", "low" or "in"
    updated_at: datetime | None


class InventoryList(BaseModel):
    items: list[InventoryRow]
    total: int
    limit: int
    offset: int
    low_stock_threshold: int


class InventoryUpdate(BaseModel):
    """Only physical stock can be set. `reserved` is controlled by orders."""

    model_config = ConfigDict(extra="forbid")

    on_hand: Annotated[int, Field(strict=True, ge=0, le=100_000)]


# --- Orders --------------------------------------------------------------------------


class CustomerRef(BaseModel):
    id: int
    email: str
    name: str
    phone: str | None


class AdminOrderSummary(BaseModel):
    order_number: str
    created_at: datetime
    customer: CustomerRef
    total: int
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    city: str
    item_count: int


class AdminOrderList(BaseModel):
    items: list[AdminOrderSummary]
    total: int
    limit: int
    offset: int


class AdminStatusEvent(BaseModel):
    status: OrderStatus
    note: str | None
    internal_note: str | None
    changed_by: str | None
    created_at: datetime


class AdminPaymentEvent(BaseModel):
    from_status: PaymentStatus
    to_status: PaymentStatus
    note: str | None
    changed_by: str | None
    created_at: datetime


class AdminOrderDetail(AdminOrderSummary):
    subtotal: int
    delivery_fee: int
    discount_total: int
    delivery: DeliveryAddressSnapshot
    items: list[OrderItemResponse]
    status_history: list[AdminStatusEvent]
    payment_history: list[AdminPaymentEvent]
    timeline: list[TimelineStep]
    allowed_statuses: list[OrderStatus]
    allowed_payment_statuses: list[PaymentStatus]


class OrderStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus
    # Shown to the customer on their order page.
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    # Staff only.
    internal_note: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None


class PaymentStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_status: PaymentStatus
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


# --- Overview --------------------------------------------------------------------------


class OverviewMetrics(BaseModel):
    active_products: int
    inactive_products: int
    active_variants: int
    low_stock_variants: int
    out_of_stock_variants: int
    orders_awaiting_action: int
    orders_in_delivery: int
    orders_today: int
    customers: int
    # Sum of non-cancelled order totals. Not revenue: demo payments may be unpaid.
    order_value: int
    # Sum of orders whose (manual, demo) payment status is "paid".
    paid_order_value: int
    low_stock_threshold: int


class Overview(BaseModel):
    metrics: OverviewMetrics
    recent_orders: list[AdminOrderSummary]
    low_stock: list[InventoryRow]
