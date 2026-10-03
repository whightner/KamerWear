"""Admin requests/responses for categories, products, variants and images.

Money is whole XAF (FCFA). Prices must be JSON integers: floats and strings
are rejected rather than rounded.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models import Gender

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
# Images are static files of the web app under frontend/public/images/products/.
IMAGE_PATH_PATTERN = re.compile(
    r"^/images/products/[a-z0-9]+(?:-[a-z0-9]+)*/[A-Za-z0-9][A-Za-z0-9_-]*"
    r"(?:\.[A-Za-z0-9_-]+)*\.(?:webp|jpe?g|png|avif)$"
)
MAX_PRICE = 10_000_000


def _text(max_length: int, min_length: int = 1):
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length),
    ]


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value.strip() if isinstance(value, str) else value


def _image_path(value: str) -> str:
    value = value.strip()
    if ".." in value or not IMAGE_PATH_PATTERN.fullmatch(value):
        raise ValueError(
            "Use a web app image path like /images/products/<folder>/<file>.webp "
            "(webp, jpg, png or avif)."
        )
    return value


def _sku(value: str) -> str:
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{1,39}", value):
        raise ValueError("Use 2–40 letters, digits or dashes, e.g. UR02-BLACK-43.")
    return value


Slug = Annotated[
    str,
    StringConstraints(max_length=120, pattern=SLUG_PATTERN),
    BeforeValidator(lambda v: v.strip().lower() if isinstance(v, str) else v),
]
Price = Annotated[int, Field(strict=True, ge=0, le=MAX_PRICE)]


def _optional(max_length: int):
    """Optional text: blank becomes null; otherwise trimmed and length-checked."""
    return Annotated[
        Annotated[str, StringConstraints(max_length=max_length)] | None,
        BeforeValidator(_blank_to_none),
    ]


Sku = Annotated[str, AfterValidator(_sku)]
ColorHex = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^#[0-9a-fA-F]{6}$")]
ImagePath = Annotated[str, AfterValidator(_image_path)]
Size = _optional(10)


# --- Categories ------------------------------------------------------------------


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: _text(80)
    slug: Slug
    description: _optional(1000) = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: _text(80) | None = None
    slug: Slug | None = None
    description: _optional(1000) = None
    is_active: bool | None = None


class AdminCategory(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool
    product_count: int
    active_product_count: int


# --- Products ------------------------------------------------------------------


def check_compare_at(base_price: int | None, compare_at: int | None) -> None:
    if base_price is not None and compare_at is not None and compare_at <= base_price:
        raise ValueError(
            "The compare-at (original) price must be higher than the price, or left empty."
        )


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: _text(120)
    slug: Slug
    category_id: int
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] = ""
    gender: Gender
    product_type: _text(50)
    base_price: Price
    compare_at_price: Price | None = None
    smart_fit: bool = False
    smart_fit_demo_size: _optional(10) = None
    is_new: bool = False
    featured: bool = False
    # New products start hidden: add variants, stock and images, then activate.
    is_active: bool = False
    search_keywords: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""

    @model_validator(mode="after")
    def _prices(self):
        check_compare_at(self.base_price, self.compare_at_price)
        return self


class ProductUpdate(BaseModel):
    """Only the fields sent change. compare_at_price: null removes it."""

    model_config = ConfigDict(extra="forbid")

    name: _text(120) | None = None
    slug: Slug | None = None
    category_id: int | None = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None
    ) = None
    gender: Gender | None = None
    product_type: _text(50) | None = None
    base_price: Price | None = None
    compare_at_price: Price | None = None
    smart_fit: bool | None = None
    smart_fit_demo_size: _optional(10) = None
    is_new: bool | None = None
    featured: bool | None = None
    is_active: bool | None = None
    search_keywords: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None
    ) = None


class CategoryRef(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool


class AdminProductListItem(BaseModel):
    id: int
    name: str
    slug: str
    category: CategoryRef
    base_price: int
    compare_at_price: int | None
    is_active: bool
    # Active product in an active category: shown in the shop.
    visible_in_shop: bool
    image_path: str | None
    variant_count: int
    active_variant_count: int
    available_quantity: int
    low_stock_variant_count: int
    updated_at: datetime


class AdminProductList(BaseModel):
    items: list[AdminProductListItem]
    total: int
    limit: int
    offset: int


class AdminImage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_path: str
    alt_text: str
    position: int
    color_name: str | None


class AdminVariant(BaseModel):
    id: int
    sku: str
    size: str | None
    color_name: str
    color_hex: str
    price_override: int | None
    price: int
    is_active: bool
    on_hand: int
    reserved: int
    available_quantity: int
    stock_state: str  # "out", "low" or "in"


class AdminProductDetail(BaseModel):
    id: int
    name: str
    slug: str
    category: CategoryRef
    description: str
    gender: Gender
    product_type: str
    base_price: int
    compare_at_price: int | None
    smart_fit: bool
    smart_fit_demo_size: str | None
    is_new: bool
    featured: bool
    is_active: bool
    visible_in_shop: bool
    search_keywords: str
    # Seeded demo review data, read-only here.
    rating_average: Decimal
    review_count: int
    images: list[AdminImage]
    variants: list[AdminVariant]
    created_at: datetime
    updated_at: datetime


# --- Variants ------------------------------------------------------------------


class VariantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: Sku
    size: Size = None
    color_name: _text(50)
    color_hex: ColorHex
    price_override: Price | None = None
    is_active: bool = True
    # Starting physical stock; change it later on the inventory page.
    on_hand: Annotated[int, Field(strict=True, ge=0, le=100_000)] = 0


class VariantUpdate(BaseModel):
    """Only the fields sent change. price_override: null uses the product price."""

    model_config = ConfigDict(extra="forbid")

    sku: Sku | None = None
    size: Size = None
    color_name: _text(50) | None = None
    color_hex: ColorHex | None = None
    price_override: Price | None = None
    is_active: bool | None = None


# --- Images ------------------------------------------------------------------------


class ImageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_path: ImagePath
    alt_text: _text(255)
    # Omit to add at the end of the gallery.
    position: Annotated[int, Field(strict=True, ge=0, le=1000)] | None = None
    # Shows this photo when the colour is selected; empty = every colour.
    color_name: _optional(50) = None


class ImageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_path: ImagePath | None = None
    alt_text: _text(255) | None = None
    position: Annotated[int, Field(strict=True, ge=0, le=1000)] | None = None
    color_name: _optional(50) = None
