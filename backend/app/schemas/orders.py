"""Checkout quote and order requests/responses."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.address import AddressResponse
from app.schemas.cart import CartLine

DEMO_PAYMENT_NOTES = {
    PaymentMethod.mobile_money: "Demo payment — real payment integration is not enabled. "
    "No Mobile Money request will be sent.",
    PaymentMethod.card: "Demo payment — real payment integration is not enabled. "
    "No card details are collected.",
    PaymentMethod.cash_on_delivery: "Pay the courier in cash when your order arrives.",
}


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_id: int | None = None
    payment_method: PaymentMethod | None = None


class QuoteResponse(BaseModel):
    items: list[CartLine]
    item_count: int
    subtotal: int
    # Null until an address is chosen.
    delivery_fee: int | None
    discount_total: int
    total: int
    address: AddressResponse | None
    payment_method: PaymentMethod | None
    payment_note: str | None
    # Messages that block ordering (empty cart, stock problems, no address...).
    issues: list[str]
    can_place_order: bool


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_id: int
    payment_method: PaymentMethod
    # The total the customer saw. If the server's total differs, nothing is
    # ordered and an updated quote must be reviewed (code "quote_changed").
    expected_total: int | None = None


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int | None
    variant_id: int | None
    product_name: str
    product_slug: str
    sku: str
    size: str | None
    color_name: str
    image_path: str | None
    unit_price: int
    quantity: int
    line_total: int


class DeliveryAddressSnapshot(BaseModel):
    label: str
    recipient_name: str
    phone: str
    country_code: str
    region: str
    city: str
    quarter: str
    landmark: str
    latitude: Decimal | None
    longitude: Decimal | None


class StatusEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: OrderStatus
    note: str | None
    created_at: datetime


class TimelineStep(BaseModel):
    status: OrderStatus
    label: str
    state: str  # "done", "current" or "upcoming"
    reached_at: datetime | None


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_number: str
    created_at: datetime
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod
    total: int
    item_count: int


class OrderListResponse(BaseModel):
    items: list[OrderSummary]
    total: int
    limit: int
    offset: int


class OrderDetail(OrderSummary):
    subtotal: int
    delivery_fee: int
    discount_total: int
    payment_note: str
    delivery: DeliveryAddressSnapshot
    items: list[OrderItemResponse]
    status_history: list[StatusEvent]
    timeline: list[TimelineStep]
    is_cancelled: bool
