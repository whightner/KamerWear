"""Catalog API response shapes. Prices are whole XAF (FCFA) integers."""

from pydantic import BaseModel, ConfigDict, Field

from app.models import Gender


class _FromModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(_FromModel):
    id: int
    name: str
    slug: str


class ProductImageResponse(_FromModel):
    image_path: str = Field(examples=["/images/products/urban-runner-02/black-1.webp"])
    alt_text: str
    position: int
    color_name: str | None


class ColorOption(BaseModel):
    name: str
    hex: str = Field(examples=["#1b1a19"])


class ProductVariantResponse(_FromModel):
    id: int
    sku: str = Field(examples=["UR02-BLACK-43"])
    size: str | None = Field(description="Null for one-size products.")
    color_name: str
    color_hex: str
    price: int = Field(description="Effective price: variant override or product price.")
    in_stock: bool
    available_quantity: int = Field(description="on_hand - reserved, never below 0.")


class ProductListItem(_FromModel):
    id: int
    slug: str
    name: str
    category: CategoryResponse
    gender: Gender
    product_type: str
    price: int = Field(examples=[28500])
    compare_at_price: int | None = Field(examples=[39900])
    discount_percent: int | None = Field(examples=[29])
    # Ratings aren't money, so a JSON number is fine here (stored as NUMERIC(2,1)).
    rating_average: float = Field(examples=[4.7])
    review_count: int
    smart_fit: bool
    is_new: bool
    featured: bool
    primary_image: ProductImageResponse | None
    sizes: list[str]
    colors: list[ColorOption]
    in_stock: bool
    available_quantity: int


class ProductListResponse(BaseModel):
    items: list[ProductListItem]
    total: int
    limit: int
    offset: int


class ProductDetail(ProductListItem):
    description: str
    smart_fit_demo_size: str | None = Field(
        description="Demo-only size for the Smart Fit preview (no real Fit Profiles yet)."
    )
    images: list[ProductImageResponse]
    # Read from the model's active variants; serialized as "variants".
    variants: list[ProductVariantResponse] = Field(validation_alias="active_variants")


class ErrorDetail(BaseModel):
    code: str = Field(examples=["product_not_found"])
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail
