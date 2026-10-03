"""Cart requests and responses. Prices and stock always come from the catalog."""

from pydantic import BaseModel, ConfigDict, Field

MAX_LINE_QUANTITY = 10


class CartItemAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: int
    quantity: int = Field(default=1, ge=1, le=MAX_LINE_QUANTITY)


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(ge=1, le=MAX_LINE_QUANTITY)


class CartMergeRequest(BaseModel):
    """Lines of a guest (browser-only) cart, added after login. Only ids and
    quantities are read; any price the browser had is ignored."""

    model_config = ConfigDict(extra="forbid")

    items: list[CartItemAdd] = Field(max_length=50)


class CartVariant(BaseModel):
    id: int
    sku: str
    size: str | None
    color_name: str


class CartProductImage(BaseModel):
    image_path: str
    alt_text: str


class CartProduct(BaseModel):
    id: int
    slug: str
    name: str
    category_slug: str
    image: CartProductImage | None


class CartLine(BaseModel):
    cart_item_id: int
    quantity: int
    variant: CartVariant
    product: CartProduct
    unit_price: int
    line_total: int
    available_quantity: int
    # Null when the line can be ordered; otherwise why not (sold out, too few left...).
    issue: str | None


class CartResponse(BaseModel):
    items: list[CartLine]
    subtotal: int
    item_count: int
    has_issues: bool


class CartAdjustment(BaseModel):
    variant_id: int
    product_name: str | None
    requested: int
    added: int
    message: str


class CartMergeResponse(BaseModel):
    cart: CartResponse
    adjustments: list[CartAdjustment]
