"""Return requests: customer and admin requests/responses.

Prices, totals and the owner are never accepted from the client: the server
reads them from the customer's own order.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import OrderStatus, PaymentMethod, PaymentStatus, ReturnReason, ReturnStatus
from app.schemas.admin_store import CustomerRef

Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ReturnableItem(BaseModel):
    order_item_id: int
    product_name: str
    product_slug: str
    sku: str
    size: str | None
    color_name: str
    image_path: str | None
    unit_price: int
    purchased_quantity: int
    # In requests that are not rejected or cancelled.
    already_returned: int
    returnable_quantity: int


class ReturnRef(BaseModel):
    return_number: str
    status: ReturnStatus
    created_at: datetime


class ReturnEligibility(BaseModel):
    order_number: str
    eligible: bool
    # Why not, when not eligible: return_not_eligible, return_window_expired, ...
    code: str | None
    message: str | None
    delivered_at: datetime | None
    return_deadline: datetime | None
    window_days: int
    items: list[ReturnableItem]
    returns: list[ReturnRef]


class ReturnItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_item_id: Annotated[int, Field(strict=True, ge=1)]
    quantity: Annotated[int, Field(strict=True, ge=1, le=100)]
    reason: ReturnReason
    note: Note | None = None


class ReturnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]
    items: Annotated[list[ReturnItemCreate], Field(min_length=1, max_length=50)]
    customer_note: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None
    ) = None


class ReturnCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: Note | None = None


class ReturnItemResponse(BaseModel):
    id: int
    order_item_id: int
    product_name: str
    product_slug: str
    sku: str
    size: str | None
    color_name: str
    image_path: str | None
    unit_price: int  # purchase-time price
    quantity: int
    line_value: int
    reason: ReturnReason
    condition_note: str | None


class ReturnEvent(BaseModel):
    status: ReturnStatus
    note: str | None
    created_at: datetime


class ReturnSummary(BaseModel):
    return_number: str
    order_number: str
    status: ReturnStatus
    reason_summary: str
    item_count: int
    return_value: int
    created_at: datetime


class ReturnDetail(ReturnSummary):
    customer_note: str | None
    updated_at: datetime
    resolved_at: datetime | None
    refunded_amount: int | None
    # Shown once refunded: makes clear no payment provider was involved.
    refund_note: str | None
    can_cancel: bool
    items: list[ReturnItemResponse]
    history: list[ReturnEvent]


class ReturnList(BaseModel):
    items: list[ReturnSummary]
    total: int
    limit: int
    offset: int


# --- Admin -------------------------------------------------------------------------


class AdminReturnSummary(ReturnSummary):
    customer: CustomerRef


class AdminReturnList(BaseModel):
    items: list[AdminReturnSummary]
    total: int
    limit: int
    offset: int


class AdminReturnItem(ReturnItemResponse):
    variant_id: int | None
    # Staff decision when received: True = back on sale, False = not, None = not yet.
    restock: bool | None


class AdminReturnEvent(BaseModel):
    status: ReturnStatus
    note: str | None
    internal_note: str | None
    changed_by: str | None
    created_at: datetime


class AdminReturnOrder(BaseModel):
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod
    total: int
    delivery_fee: int
    delivered_at: datetime | None


class AdminReturnDetail(AdminReturnSummary):
    customer_note: str | None
    updated_at: datetime
    resolved_at: datetime | None
    refunded_amount: int | None
    refund_note: str | None
    order: AdminReturnOrder
    items: list[AdminReturnItem]
    history: list[AdminReturnEvent]
    # Next steps staff may take: approve, reject, receive, refund.
    allowed_actions: list[str]
    # True when recording the refund may also mark the whole order payment refunded.
    can_mark_order_refunded: bool


class ReturnDecision(BaseModel):
    """Approve or reject. `note` is shown to the customer; `internal_note` is not."""

    model_config = ConfigDict(extra="forbid")

    note: Note | None = None
    internal_note: Note | None = None


class ReceivedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    return_item_id: Annotated[int, Field(strict=True, ge=1)]
    restock: bool


class ReturnReceive(ReturnDecision):
    """Every returned line needs an explicit restock decision."""

    items: Annotated[list[ReceivedItem], Field(min_length=1, max_length=50)]


class ReturnRefund(ReturnDecision):
    """Records a demo/manual refund. No payment provider is contacted."""

    mark_order_payment_refunded: bool = False
