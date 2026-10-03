"""Smart Fit requests and responses. Photos and pose data are never returned."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import FitPreference

Confidence = Literal["high", "medium", "low"]


class FitMeasurements(BaseModel):
    """Approximate body dimensions in cm (null = not estimated). Not tailor measurements."""

    shoulder_width_cm: float | None = Field(
        description="Distance between the shoulder joints, not a tailor's shoulder seam."
    )
    chest_cm: float | None
    waist_cm: float | None
    hip_cm: float | None
    inseam_cm: float | None


class FitSuggestedSizes(BaseModel):
    top: str | None = Field(examples=["M"])
    bottom: str | None = Field(examples=["32"])


class FitEstimateResponse(BaseModel):
    """A photo estimate for the customer to review. It is not saved as the profile."""

    estimate_id: int
    height_cm: int
    fit_preference: FitPreference
    used_side_photo: bool
    measurements: FitMeasurements
    suggested: FitSuggestedSizes
    # The same measurements with each fit preference, so the review screen can
    # switch preference without another upload.
    suggested_by_preference: dict[FitPreference, FitSuggestedSizes]
    size_notes: list[str]
    confidence: Confidence = Field(
        description="How much the photos supported the estimate. Not an accuracy figure."
    )
    confidence_factors: list[str]
    warnings: list[str]
    estimation_version: str
    size_chart_version: str
    created_at: datetime


class FitProfileUpdate(BaseModel):
    """What the customer confirmed. Measurements are copied from their own estimate."""

    model_config = ConfigDict(extra="forbid")

    estimate_id: Annotated[int, Field(strict=True, ge=1)] | None = None
    height_cm: Annotated[int, Field(strict=True, ge=100, le=230)]
    fit_preference: FitPreference = FitPreference.regular
    top_size: Annotated[str, Field(max_length=10)] | None = None
    bottom_size: Annotated[str, Field(max_length=10)] | None = None
    shoe_size_eu: Annotated[int, Field(strict=True)] | None = None


class FitProfileResponse(BaseModel):
    height_cm: int
    fit_preference: FitPreference
    top_size: str | None
    bottom_size: str | None
    bottom_size_letter: str | None = Field(description="Letter equivalent, e.g. 32 -> M.")
    shoe_size_eu: int | None = Field(description="Entered by the customer, never estimated.")
    estimated_measurements: FitMeasurements
    source: Literal["photo_estimate", "photo_corrected", "manual"]
    confidence: Confidence | None
    estimation_version: str | None
    confirmed_by_user: bool
    created_at: datetime
    updated_at: datetime


class ProductFitRecommendation(BaseModel):
    status: Literal[
        "recommended", "unavailable", "not_offered", "missing_size", "no_profile", "unsupported"
    ]
    kind: Literal["top", "bottom", "shoe"] | None
    size: str | None = Field(description="The product size matching the Fit Profile.")
    size_label: str | None = Field(examples=["M", "EU 43"])
    nearest_available: str | None
    source: str | None
    confidence: Confidence | None
    message: str | None
