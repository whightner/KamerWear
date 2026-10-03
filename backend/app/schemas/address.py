"""Delivery address requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.auth import normalize_phone

# The ten regions of Cameroon, as shown in the address form.
CAMEROON_REGIONS = (
    "Adamawa",
    "Centre",
    "East",
    "Far North",
    "Littoral",
    "North",
    "North-West",
    "South",
    "South-West",
    "West",
)


def _region(value: str) -> str:
    for region in CAMEROON_REGIONS:
        if region.lower() == value.lower():
            return region
    raise ValueError(f"Choose one of: {', '.join(CAMEROON_REGIONS)}.")


def _required_phone(value: str) -> str:
    phone = normalize_phone(value)
    if phone is None:
        raise ValueError("Enter a phone number the courier can call.")
    return phone


def _text(max_length: int):
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length),
    ]


Region = Annotated[str, AfterValidator(_region)]
Phone = Annotated[str, Field(max_length=30), AfterValidator(_required_phone)]
Latitude = Annotated[Decimal | None, Field(ge=-90, le=90, decimal_places=6)]
Longitude = Annotated[Decimal | None, Field(ge=-180, le=180, decimal_places=6)]


class AddressCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: _text(40) = "Home"
    recipient_name: _text(120)
    phone: Phone
    region: Region
    city: _text(80)
    quarter: _text(80)
    street_or_landmark: _text(255)
    latitude: Latitude = None
    longitude: Longitude = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    """Only the fields sent are changed. Setting is_default=true moves the default."""

    model_config = ConfigDict(extra="forbid")

    label: _text(40) | None = None
    recipient_name: _text(120) | None = None
    phone: Phone | None = None
    region: Region | None = None
    city: _text(80) | None = None
    quarter: _text(80) | None = None
    street_or_landmark: _text(255) | None = None
    latitude: Latitude = None
    longitude: Longitude = None
    is_default: bool | None = None


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    recipient_name: str
    phone: str
    country_code: str
    region: str
    city: str
    quarter: str
    street_or_landmark: str
    latitude: Decimal | None
    longitude: Decimal | None
    is_default: bool
    created_at: datetime
    updated_at: datetime
