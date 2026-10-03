"""Returns: a customer's request to send back delivered items.

A return points at the original order and its immutable order lines (name,
SKU, size and price at purchase time), so nothing from the catalog is copied
again. Store staff move it through a fixed state machine; every change is
recorded in return_status_history.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.order import OrderItem, _enum


class ReturnStatus(enum.StrEnum):
    requested = "requested"
    approved = "approved"
    rejected = "rejected"
    received = "received"
    refunded = "refunded"
    cancelled = "cancelled"


class ReturnReason(enum.StrEnum):
    wrong_size = "wrong_size"
    damaged = "damaged"
    wrong_item = "wrong_item"
    not_as_expected = "not_as_expected"
    changed_mind = "changed_mind"
    other = "other"


class ReturnRequest(Base):
    __tablename__ = "return_requests"
    __table_args__ = (
        CheckConstraint("return_value >= 0", name="return_value_non_negative"),
        CheckConstraint(
            "refunded_amount IS NULL OR refunded_amount >= 0", name="refunded_amount_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Customer-facing reference, e.g. KR-2026-8M4PQ2 (random, not sequential).
    return_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[ReturnStatus] = mapped_column(
        _enum(ReturnStatus, "return_status"), default=ReturnStatus.requested, index=True
    )
    # Readable list of the item reasons, e.g. "Wrong size, Item damaged".
    reason_summary: Mapped[str] = mapped_column(String(120))
    customer_note: Mapped[str | None] = mapped_column(String(1000))
    # Merchandise value in whole XAF: purchase-time unit price x quantity.
    # Delivery fees are not included.
    return_value: Mapped[int] = mapped_column(Integer)
    # Set when staff record the demo/manual refund. No provider is involved.
    refunded_amount: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # When it reached a final state (rejected, refunded or cancelled).
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["ReturnItem"]] = relationship(
        back_populates="return_request", cascade="all, delete-orphan", order_by="ReturnItem.id"
    )
    status_history: Mapped[list["ReturnStatusHistory"]] = relationship(
        back_populates="return_request",
        cascade="all, delete-orphan",
        order_by="ReturnStatusHistory.id",
    )

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)


class ReturnItem(Base):
    __tablename__ = "return_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        UniqueConstraint(
            "return_request_id", "order_item_id", name="uq_return_items_request_order_item"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    return_request_id: Mapped[int] = mapped_column(
        ForeignKey("return_requests.id", ondelete="CASCADE"), index=True
    )
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[ReturnReason] = mapped_column(_enum(ReturnReason, "return_reason"))
    condition_note: Mapped[str | None] = mapped_column(String(500))
    # Decided by staff when the parcel is received: True = back on sale.
    restock: Mapped[bool | None] = mapped_column(Boolean)

    return_request: Mapped[ReturnRequest] = relationship(back_populates="items")
    order_item: Mapped[OrderItem] = relationship()


class ReturnStatusHistory(Base):
    __tablename__ = "return_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    return_request_id: Mapped[int] = mapped_column(
        ForeignKey("return_requests.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ReturnStatus] = mapped_column(_enum(ReturnStatus, "return_status"))
    # Who made the change: the customer (request, cancel) or a staff member.
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # Shown to the customer.
    customer_note: Mapped[str | None] = mapped_column(String(500))
    # Staff only; never returned by customer endpoints.
    internal_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    return_request: Mapped[ReturnRequest] = relationship(back_populates="status_history")
