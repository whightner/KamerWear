"""Saved delivery addresses of a customer."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Address(Base):
    """A Cameroon-style delivery address: region, city, quarter and a landmark.

    Many places have no street number, so `street_or_landmark` holds whatever
    helps the courier ("Near Tradex, blue gate"). Orders copy these fields, so
    editing or deleting an address never changes an existing order.
    """

    __tablename__ = "addresses"
    __table_args__ = (
        # At most one default address per customer.
        Index(
            "uq_addresses_user_id_default",
            "user_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40))  # e.g. "Home", "Office"
    recipient_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    country_code: Mapped[str] = mapped_column(String(2), default="CM", server_default="CM")
    region: Mapped[str] = mapped_column(String(40))
    city: Mapped[str] = mapped_column(String(80))
    quarter: Mapped[str] = mapped_column(String(80))
    street_or_landmark: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
