"""Admin catalog management: categories, products, variants and image metadata.

Nothing here hard-deletes products, categories or variants: deactivating keeps
carts, orders and history intact (order lines are snapshots anyway). Inactive
items disappear from the shop and can't be bought. Image metadata rows can be
removed; the image files themselves are static assets of the web app.
"""

from sqlalchemy import Integer, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import LOW_STOCK_THRESHOLD
from app.models import Category, Inventory, Product, ProductImage, ProductVariant
from app.schemas.admin_catalog import (
    AdminCategory,
    AdminImage,
    AdminProductDetail,
    AdminProductListItem,
    AdminVariant,
    CategoryCreate,
    CategoryRef,
    CategoryUpdate,
    ImageCreate,
    ImageUpdate,
    ProductCreate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
    check_compare_at,
)
from app.services.errors import ServiceError, not_found


def stock_state(available: int) -> str:
    if available <= 0:
        return "out"
    if available <= LOW_STOCK_THRESHOLD:
        return "low"
    return "in"


def _conflict(code: str, message: str) -> ServiceError:
    return ServiceError(409, code, message)


def _invalid(field: str, message: str) -> ServiceError:
    return ServiceError(
        422, "validation_error", "Some fields are invalid.", fields={field: message}
    )


# --- Categories ------------------------------------------------------------------


def category_not_found() -> ServiceError:
    return not_found("category_not_found", "This category doesn't exist.")


def list_categories(db: Session) -> list[AdminCategory]:
    rows = db.execute(
        select(
            Category,
            func.count(Product.id),
            func.count(Product.id).filter(Product.is_active.is_(True)),
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    ).all()
    return [
        AdminCategory(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            is_active=c.is_active,
            product_count=total,
            active_product_count=active,
        )
        for c, total, active in rows
    ]


def _category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise category_not_found()
    return category


def _ensure_category_slug_free(db: Session, slug: str, exclude_id: int | None = None) -> None:
    query = select(Category.id).where(Category.slug == slug)
    if exclude_id is not None:
        query = query.where(Category.id != exclude_id)
    if db.scalar(query) is not None:
        raise _conflict("slug_already_exists", f"Another category already uses the slug '{slug}'.")


def create_category(db: Session, data: CategoryCreate) -> Category:
    _ensure_category_slug_free(db, data.slug)
    category = Category(**data.model_dump())
    db.add(category)
    db.flush()
    return category


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = _category(db, category_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "slug", "is_active"):
        if changes.get(field, ...) is None:
            changes.pop(field)  # required fields: null means "unchanged"
    if "slug" in changes:
        _ensure_category_slug_free(db, changes["slug"], exclude_id=category.id)
    for field, value in changes.items():
        setattr(category, field, value)
    db.flush()
    return category


def category_summary(db: Session, category_id: int) -> AdminCategory:
    return next(c for c in list_categories(db) if c.id == category_id)


# --- Products ------------------------------------------------------------------


def product_not_found() -> ServiceError:
    return not_found("product_not_found", "This product doesn't exist.")


def _available():
    return func.greatest(Inventory.on_hand - Inventory.reserved, 0)


def list_products(
    db: Session,
    *,
    q: str | None,
    category_id: int | None,
    status: str | None,
    low_stock: bool,
    limit: int,
    offset: int,
) -> tuple[list[AdminProductListItem], int]:
    """Products with per-product stock figures computed by one aggregate query."""
    available = _available()
    active_variant = ProductVariant.is_active.is_(True)
    stats = (
        select(
            ProductVariant.product_id.label("product_id"),
            func.count(ProductVariant.id).label("variant_count"),
            func.count(ProductVariant.id).filter(active_variant).label("active_variant_count"),
            func.coalesce(func.sum(case((active_variant, available), else_=0)), 0)
            .cast(Integer)
            .label("available_quantity"),
            func.count(ProductVariant.id)
            .filter(active_variant, available <= LOW_STOCK_THRESHOLD)
            .label("low_stock_variant_count"),
        )
        .outerjoin(Inventory, Inventory.variant_id == ProductVariant.id)
        .group_by(ProductVariant.product_id)
        .subquery()
    )
    first_image = (
        select(ProductImage.image_path)
        .where(ProductImage.product_id == Product.id)
        .order_by(ProductImage.position, ProductImage.id)
        .limit(1)
        .scalar_subquery()
    )
    query = (
        select(
            Product,
            Category,
            first_image.label("image_path"),
            func.coalesce(stats.c.variant_count, 0),
            func.coalesce(stats.c.active_variant_count, 0),
            func.coalesce(stats.c.available_quantity, 0),
            func.coalesce(stats.c.low_stock_variant_count, 0),
        )
        .join(Category, Category.id == Product.category_id)
        .outerjoin(stats, stats.c.product_id == Product.id)
    )
    if q:
        pattern = f"%{q.strip()}%"
        sku_match = (
            select(ProductVariant.id)
            .where(ProductVariant.product_id == Product.id, ProductVariant.sku.ilike(pattern))
            .exists()
        )
        query = query.where(
            or_(Product.name.ilike(pattern), Product.slug.ilike(pattern), sku_match)
        )
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if status == "active":
        query = query.where(Product.is_active.is_(True))
    elif status == "inactive":
        query = query.where(Product.is_active.is_(False))
    if low_stock:
        query = query.where(func.coalesce(stats.c.low_stock_variant_count, 0) > 0)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(Product.name, Product.id).limit(limit).offset(offset)).all()
    items = [
        AdminProductListItem(
            id=product.id,
            name=product.name,
            slug=product.slug,
            category=CategoryRef(
                id=category.id, name=category.name, slug=category.slug, is_active=category.is_active
            ),
            base_price=product.base_price,
            compare_at_price=product.compare_at_price,
            is_active=product.is_active,
            visible_in_shop=product.is_active and category.is_active,
            image_path=image_path,
            variant_count=variant_count,
            active_variant_count=active_count,
            available_quantity=available_qty,
            low_stock_variant_count=low_count,
            updated_at=product.updated_at,
        )
        for product, category, image_path, variant_count, active_count, available_qty, low_count in rows
    ]
    return items, total


def _load_product(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.inventory),
        )
        .execution_options(populate_existing=True)
    )
    if product is None:
        raise product_not_found()
    return product


def admin_variant(variant: ProductVariant) -> AdminVariant:
    inventory = variant.inventory
    on_hand = inventory.on_hand if inventory else 0
    reserved = inventory.reserved if inventory else 0
    available = max(0, on_hand - reserved)
    return AdminVariant(
        id=variant.id,
        sku=variant.sku,
        size=variant.size,
        color_name=variant.color_name,
        color_hex=variant.color_hex,
        price_override=variant.price_override,
        price=variant.price,
        is_active=variant.is_active,
        on_hand=on_hand,
        reserved=reserved,
        available_quantity=available,
        stock_state=stock_state(available),
    )


def product_detail(db: Session, product_id: int) -> AdminProductDetail:
    product = _load_product(db, product_id)
    category = product.category
    return AdminProductDetail(
        id=product.id,
        name=product.name,
        slug=product.slug,
        category=CategoryRef(
            id=category.id, name=category.name, slug=category.slug, is_active=category.is_active
        ),
        description=product.description,
        gender=product.gender,
        product_type=product.product_type,
        base_price=product.base_price,
        compare_at_price=product.compare_at_price,
        smart_fit=product.smart_fit,
        smart_fit_demo_size=product.smart_fit_demo_size,
        is_new=product.is_new,
        featured=product.featured,
        is_active=product.is_active,
        visible_in_shop=product.is_active and category.is_active,
        search_keywords=product.search_keywords,
        rating_average=product.rating_average,
        review_count=product.review_count,
        images=[AdminImage.model_validate(image) for image in product.images],
        variants=[admin_variant(v) for v in product.variants],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _ensure_product_slug_free(db: Session, slug: str, exclude_id: int | None = None) -> None:
    query = select(Product.id).where(Product.slug == slug)
    if exclude_id is not None:
        query = query.where(Product.id != exclude_id)
    if db.scalar(query) is not None:
        raise _conflict("slug_already_exists", f"Another product already uses the slug '{slug}'.")


def create_product(db: Session, data: ProductCreate) -> Product:
    _category(db, data.category_id)
    _ensure_product_slug_free(db, data.slug)
    product = Product(**data.model_dump())
    db.add(product)
    db.flush()
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = _load_product(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    for field in (
        "name",
        "slug",
        "category_id",
        "description",
        "gender",
        "product_type",
        "base_price",
        "smart_fit",
        "is_new",
        "featured",
        "is_active",
        "search_keywords",
    ):
        if changes.get(field, ...) is None:
            changes.pop(field)  # required fields: null means "unchanged"
    if "category_id" in changes:
        _category(db, changes["category_id"])
    if "slug" in changes:
        _ensure_product_slug_free(db, changes["slug"], exclude_id=product.id)
    base_price = changes.get("base_price", product.base_price)
    compare_at = changes.get("compare_at_price", product.compare_at_price)
    try:
        check_compare_at(base_price, compare_at)
    except ValueError as exc:
        raise _invalid("compare_at_price", str(exc)) from None
    for field, value in changes.items():
        setattr(product, field, value)
    db.flush()
    return product


# --- Variants --------------------------------------------------------------------


def variant_not_found() -> ServiceError:
    return not_found("variant_not_found", "This variant doesn't exist.")


def _ensure_sku_free(db: Session, sku: str, exclude_id: int | None = None) -> None:
    query = select(ProductVariant.id).where(ProductVariant.sku == sku)
    if exclude_id is not None:
        query = query.where(ProductVariant.id != exclude_id)
    if db.scalar(query) is not None:
        raise _conflict("sku_already_exists", f"The SKU {sku} is already used by another variant.")


def _ensure_combination_free(
    db: Session, product_id: int, color: str, size: str | None, exclude_id: int | None = None
) -> None:
    """One variant per colour and size, so the shop's selectors stay unambiguous."""
    query = select(ProductVariant.sku).where(
        ProductVariant.product_id == product_id,
        func.lower(ProductVariant.color_name) == color.lower(),
        ProductVariant.size.is_(None) if size is None else ProductVariant.size == size,
    )
    if exclude_id is not None:
        query = query.where(ProductVariant.id != exclude_id)
    existing = db.scalar(query)
    if existing is not None:
        label = f"{color} / {size}" if size else color
        raise _conflict(
            "variant_already_exists", f"This product already has a {label} variant ({existing})."
        )


def create_variant(db: Session, product_id: int, data: VariantCreate) -> ProductVariant:
    product = _load_product(db, product_id)
    _ensure_sku_free(db, data.sku)
    _ensure_combination_free(db, product.id, data.color_name, data.size)
    variant = ProductVariant(
        product_id=product.id,
        **data.model_dump(exclude={"on_hand"}),
    )
    variant.inventory = Inventory(on_hand=data.on_hand, reserved=0)
    db.add(variant)
    try:
        db.flush()
    except IntegrityError:  # a concurrent request took the SKU first
        db.rollback()
        raise _conflict("sku_already_exists", f"The SKU {data.sku} is already used.") from None
    return variant


def _variant(db: Session, variant_id: int) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == variant_id)
        .options(joinedload(ProductVariant.inventory), joinedload(ProductVariant.product))
    )
    if variant is None:
        raise variant_not_found()
    return variant


def update_variant(db: Session, variant_id: int, data: VariantUpdate) -> ProductVariant:
    """Edits a variant. Past orders keep their own copy of SKU, size and colour."""
    variant = _variant(db, variant_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("sku", "color_name", "color_hex", "is_active"):
        if changes.get(field, ...) is None:
            changes.pop(field)
    if "sku" in changes:
        _ensure_sku_free(db, changes["sku"], exclude_id=variant.id)
    if "color_name" in changes or "size" in changes:
        _ensure_combination_free(
            db,
            variant.product_id,
            changes.get("color_name", variant.color_name),
            changes.get("size", variant.size),
            exclude_id=variant.id,
        )
    for field, value in changes.items():
        setattr(variant, field, value)
    db.flush()
    return variant


# --- Images ------------------------------------------------------------------------


def image_not_found() -> ServiceError:
    return not_found("image_not_found", "This image doesn't exist.")


def _ensure_image_free(
    db: Session, product_id: int, path: str, exclude_id: int | None = None
) -> None:
    query = select(ProductImage.id).where(
        ProductImage.product_id == product_id, ProductImage.image_path == path
    )
    if exclude_id is not None:
        query = query.where(ProductImage.id != exclude_id)
    if db.scalar(query) is not None:
        raise _conflict("image_already_exists", "This product already has an image with that path.")


def create_image(db: Session, product_id: int, data: ImageCreate) -> ProductImage:
    product = _load_product(db, product_id)
    _ensure_image_free(db, product.id, data.image_path)
    position = data.position
    if position is None:
        last = db.scalar(
            select(func.max(ProductImage.position)).where(ProductImage.product_id == product.id)
        )
        position = 0 if last is None else last + 1
    image = ProductImage(
        product_id=product.id,
        image_path=data.image_path,
        alt_text=data.alt_text,
        position=position,
        color_name=data.color_name,
    )
    db.add(image)
    db.flush()
    return image


def _image(db: Session, image_id: int) -> ProductImage:
    image = db.get(ProductImage, image_id)
    if image is None:
        raise image_not_found()
    return image


def update_image(db: Session, image_id: int, data: ImageUpdate) -> ProductImage:
    image = _image(db, image_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("image_path", "alt_text", "position"):
        if changes.get(field, ...) is None:
            changes.pop(field)
    if "image_path" in changes:
        _ensure_image_free(db, image.product_id, changes["image_path"], exclude_id=image.id)
    for field, value in changes.items():
        setattr(image, field, value)
    db.flush()
    return image


def delete_image(db: Session, image_id: int) -> int:
    """Removes the image metadata (not the file). Returns the product id."""
    image = _image(db, image_id)
    product_id = image.product_id
    db.delete(image)
    db.flush()
    return product_id
