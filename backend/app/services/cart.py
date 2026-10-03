"""The signed-in customer's persistent cart.

The owner always comes from authentication, never from the request body.
Lines store only a variant id and a quantity; product details, the effective
price and availability are resolved from the catalog on every read.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Cart, CartItem, Product, ProductVariant, User
from app.schemas.cart import (
    MAX_LINE_QUANTITY,
    CartAdjustment,
    CartItemAdd,
    CartLine,
    CartProduct,
    CartProductImage,
    CartResponse,
    CartVariant,
)
from app.services.errors import ServiceError, not_found


def variant_label(variant: ProductVariant) -> str:
    """ "Urban Runner 02, EU 43" / "Classic Hoodie, M" / "Canvas Tote"."""
    product = variant.product
    if not variant.size:
        return product.name
    prefix = "EU " if product.category.slug == "shoes" else ""
    return f"{product.name}, {prefix}{variant.size}"


def insufficient_stock(variant: ProductVariant, available: int) -> ServiceError:
    label = variant_label(variant)
    if available <= 0:
        message = f"{label} is sold out."
    else:
        noun = "item remains" if available == 1 else "items remain"
        message = f"Only {available} {noun} for {label}."
    return ServiceError(
        409,
        "insufficient_stock",
        message,
        items=[{"variant_id": variant.id, "available_quantity": available}],
    )


def is_sellable(variant: ProductVariant) -> bool:
    product = variant.product
    return variant.is_active and product.is_active and product.category.is_active


def _load_variant(db: Session, variant_id: int) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == variant_id)
        .options(
            joinedload(ProductVariant.inventory),
            joinedload(ProductVariant.product).joinedload(Product.category),
            joinedload(ProductVariant.product).selectinload(Product.images),
        )
    )
    if variant is None or not is_sellable(variant):
        raise not_found("variant_not_found", "This product option is no longer available.")
    return variant


def cart_query(user: User):
    return (
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(
            selectinload(Cart.items)
            .joinedload(CartItem.variant)
            .options(
                joinedload(ProductVariant.inventory),
                joinedload(ProductVariant.product).joinedload(Product.category),
                joinedload(ProductVariant.product).selectinload(Product.images),
            )
        )
    )


def get_cart(db: Session, user: User) -> Cart | None:
    return db.scalar(cart_query(user))


def get_or_create_cart(db: Session, user: User) -> Cart:
    cart = get_cart(db, user)
    if cart is None:
        cart = Cart(user_id=user.id, items=[])
        db.add(cart)
        db.flush()
    return cart


def line_issue(item: CartItem) -> str | None:
    variant = item.variant
    if not is_sellable(variant):
        return "This item is no longer available."
    available = variant.available_quantity
    if available <= 0:
        return "Sold out."
    if item.quantity > available:
        return f"Only {available} left. Reduce the quantity to continue."
    return None


def image_for(variant: ProductVariant) -> CartProductImage | None:
    images = variant.product.images
    match = next((i for i in images if i.color_name == variant.color_name), None)
    image = match or (images[0] if images else None)
    return CartProductImage(image_path=image.image_path, alt_text=image.alt_text) if image else None


def build_lines(items: list[CartItem]) -> list[CartLine]:
    lines = []
    for item in items:
        variant = item.variant
        product = variant.product
        lines.append(
            CartLine(
                cart_item_id=item.id,
                quantity=item.quantity,
                variant=CartVariant(
                    id=variant.id,
                    sku=variant.sku,
                    size=variant.size,
                    color_name=variant.color_name,
                ),
                product=CartProduct(
                    id=product.id,
                    slug=product.slug,
                    name=product.name,
                    category_slug=product.category.slug,
                    image=image_for(variant),
                ),
                unit_price=variant.price,
                line_total=variant.price * item.quantity,
                available_quantity=variant.available_quantity if is_sellable(variant) else 0,
                issue=line_issue(item),
            )
        )
    return lines


def cart_response(cart: Cart | None) -> CartResponse:
    lines = build_lines(cart.items) if cart else []
    return CartResponse(
        items=lines,
        subtotal=sum(line.line_total for line in lines),
        item_count=sum(line.quantity for line in lines),
        has_issues=any(line.issue for line in lines),
    )


def read_cart(db: Session, user: User) -> CartResponse:
    db.expire_all()  # always show current prices and stock
    return cart_response(get_cart(db, user))


def _check_quantity(variant: ProductVariant, quantity: int) -> None:
    available = variant.available_quantity
    if quantity > available:
        raise insufficient_stock(variant, available)
    if quantity > MAX_LINE_QUANTITY:
        raise ServiceError(
            409,
            "quantity_limit",
            f"You can order up to {MAX_LINE_QUANTITY} of the same item.",
        )


def add_item(db: Session, user: User, data: CartItemAdd) -> None:
    """Adds a variant, or more of it if it's already in the cart."""
    variant = _load_variant(db, data.variant_id)
    cart = get_or_create_cart(db, user)
    existing = next((i for i in cart.items if i.variant_id == variant.id), None)
    new_quantity = data.quantity + (existing.quantity if existing else 0)
    _check_quantity(variant, new_quantity)
    if existing:
        existing.quantity = new_quantity
    else:
        cart.items.append(CartItem(variant=variant, quantity=new_quantity))
    db.flush()


def _own_item(db: Session, user: User, item_id: int) -> CartItem:
    item = db.scalar(
        select(CartItem).join(CartItem.cart).where(CartItem.id == item_id, Cart.user_id == user.id)
    )
    if item is None:
        raise not_found("cart_item_not_found", "This item is not in your cart.")
    return item


def update_item(db: Session, user: User, item_id: int, quantity: int) -> None:
    item = _own_item(db, user, item_id)
    variant = _load_variant(db, item.variant_id)
    # Lowering the quantity is always allowed, even if stock dropped below it.
    if quantity > item.quantity:
        _check_quantity(variant, quantity)
    item.quantity = quantity
    db.flush()


def remove_item(db: Session, user: User, item_id: int) -> None:
    db.delete(_own_item(db, user, item_id))
    db.flush()


def clear_cart(db: Session, user: User) -> None:
    cart = get_cart(db, user)
    if cart:
        cart.items.clear()
        db.flush()


def merge_items(db: Session, user: User, items: list[CartItemAdd]) -> list[CartAdjustment]:
    """Adds guest-cart lines, never beyond current stock. Returns what changed.

    Duplicate variants are combined; prices come from the catalog.
    """
    requested: dict[int, int] = {}
    for line in items:
        requested[line.variant_id] = requested.get(line.variant_id, 0) + line.quantity

    cart = get_or_create_cart(db, user)
    adjustments: list[CartAdjustment] = []
    for variant_id, quantity in requested.items():
        try:
            variant = _load_variant(db, variant_id)
        except ServiceError:
            adjustments.append(
                CartAdjustment(
                    variant_id=variant_id,
                    product_name=None,
                    requested=quantity,
                    added=0,
                    message="An item from your cart is no longer available and was removed.",
                )
            )
            continue
        existing = next((i for i in cart.items if i.variant_id == variant.id), None)
        current = existing.quantity if existing else 0
        limit = min(MAX_LINE_QUANTITY, variant.available_quantity)
        target = min(current + quantity, max(limit, current))
        added = max(0, target - current)
        if added < quantity:
            if limit <= 0:
                message = f"{variant_label(variant)} is sold out and was not added."
            else:
                message = (
                    f"Only {limit} available for {variant_label(variant)}; "
                    f"your cart now has {target}."
                )
            adjustments.append(
                CartAdjustment(
                    variant_id=variant.id,
                    product_name=variant.product.name,
                    requested=quantity,
                    added=added,
                    message=message,
                )
            )
        if added == 0:
            continue
        if existing:
            existing.quantity = target
        else:
            cart.items.append(CartItem(variant=variant, quantity=target))
    db.flush()
    return adjustments
