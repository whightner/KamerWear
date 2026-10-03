"""Smart Fit: the customer's confirmed Fit Profile and their recent estimates.

No photo is ever stored. An estimate keeps only derived numbers (estimated
body dimensions, suggested sizes, confidence) so the customer can review it;
only the last few are kept. The Fit Profile is what the customer confirmed.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FitPreference(enum.StrEnum):
    slim = "slim"
    regular = "regular"
    relaxed = "relaxed"


def _preference() -> Enum:
    return Enum(
        FitPreference,
        native_enum=False,
        length=10,
        create_constraint=True,
        name="fit_preference",
        values_callable=lambda e: [m.value for m in e],
    )


class FitEstimate(Base):
    """One photo-based estimate, waiting for (or used by) a confirmation."""

    __tablename__ = "fit_estimates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    height_cm: Mapped[int] = mapped_column(Integer)
    fit_preference: Mapped[FitPreference] = mapped_column(_preference())
    used_side_photo: Mapped[bool] = mapped_column(Boolean)
    # Estimated dimensions (cm); null when they couldn't be estimated reliably.
    shoulder_width_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    chest_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    waist_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    hip_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    inseam_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    suggested_top_size: Mapped[str | None] = mapped_column(String(10))
    suggested_bottom_size: Mapped[str | None] = mapped_column(String(10))
    confidence: Mapped[str] = mapped_column(String(10))  # "high", "medium" or "low"
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    estimation_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FitProfile(Base):
    """The customer's confirmed sizes. Only saved after they review and confirm."""

    __tablename__ = "fit_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    height_cm: Mapped[int] = mapped_column(Integer)
    fit_preference: Mapped[FitPreference] = mapped_column(_preference())
    # Confirmed by the customer (possibly corrected from the suggestion).
    top_size: Mapped[str | None] = mapped_column(String(10))
    bottom_size: Mapped[str | None] = mapped_column(String(10))
    # Entered by the customer; never estimated from photos.
    shoe_size_eu: Mapped[int | None] = mapped_column(Integer)
    # Estimated dimensions copied from the confirmed estimate (null if manual).
    estimated_shoulder_width_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    estimated_chest_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    estimated_waist_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    estimated_hip_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    estimated_inseam_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    # "photo_estimate" or "manual"; confidence only for photo estimates.
    source: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[str | None] = mapped_column(String(10))
    estimation_version: Mapped[str | None] = mapped_column(String(80))
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
