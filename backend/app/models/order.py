"""Orders, their line snapshots and status history.

An order is a historical record: it copies the delivery address and each
line's product name, SKU, size, colour, image and price at purchase time, so
later catalog or address changes never alter it.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(enum.StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    shipped = "shipped"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(enum.StrEnum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(enum.StrEnum):
    """Demo choices only: no payment provider is connected yet."""

    mobile_money = "mobile_money"
    card = "card"
    cash_on_delivery = "cash_on_delivery"


def _enum(cls: type[enum.Enum], name: str, length: int = 20) -> Enum:
    return Enum(
        cls,
        native_enum=False,
        length=length,
        create_constraint=True,
        name=name,
        values_callable=lambda e: [m.value for m in e],
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # A repeated "Place order" with the same key returns the first order.
        UniqueConstraint("user_id", "idempotency_key", name="uq_orders_user_id_idempotency_key"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("delivery_fee >= 0", name="delivery_fee_non_negative"),
        CheckConstraint("discount_total >= 0", name="discount_total_non_negative"),
        CheckConstraint("total >= 0", name="total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Customer-facing reference, e.g. KW-2026-7K4M9Q (random, not sequential).
    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))

    status: Mapped[OrderStatus] = mapped_column(
        _enum(OrderStatus, "order_status"), default=OrderStatus.pending
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus, "payment_status"), default=PaymentStatus.pending
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(_enum(PaymentMethod, "payment_method"))

    # Whole XAF (FCFA), calculated by the server.
    subtotal: Mapped[int] = mapped_column(Integer)
    delivery_fee: Mapped[int] = mapped_column(Integer)
    discount_total: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)

    # Copy of the delivery address at order time.
    delivery_label: Mapped[str] = mapped_column(String(40))
    delivery_recipient_name: Mapped[str] = mapped_column(String(120))
    delivery_phone: Mapped[str] = mapped_column(String(20))
    delivery_country_code: Mapped[str] = mapped_column(String(2))
    delivery_region: Mapped[str] = mapped_column(String(40))
    delivery_city: Mapped[str] = mapped_column(String(80))
    delivery_quarter: Mapped[str] = mapped_column(String(80))
    delivery_landmark: Mapped[str] = mapped_column(String(255))
    delivery_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    delivery_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.id",
    )
    payment_history: Mapped[list["PaymentStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PaymentStatusHistory.id",
    )

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)


class OrderItem(Base):
    """Immutable snapshot of one purchased variant."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # Kept for reference; the snapshot columns below are what the order shows.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(120))
    product_slug: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(40))
    size: Mapped[str | None] = mapped_column(String(10))
    color_name: Mapped[str] = mapped_column(String(50))
    image_path: Mapped[str | None] = mapped_column(String(255))
    unit_price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"))
    # Shown to the customer on their order page.
    note: Mapped[str | None] = mapped_column(String(255))
    # Staff-only note (e.g. "Customer unreachable"), never sent to customers.
    internal_note: Mapped[str | None] = mapped_column(String(500))
    # The admin who made the change; null for the customer's own checkout.
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="status_history")


class PaymentStatusHistory(Base):
    """Manual (demo) payment-status changes made by staff. No provider is involved."""

    __tablename__ = "payment_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus, "from_status"))
    to_status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus, "to_status"))
    note: Mapped[str | None] = mapped_column(String(500))
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="payment_history")
