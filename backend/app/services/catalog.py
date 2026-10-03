"""Catalog queries: filtering, search, sorting, product detail and similar items.

Every query loads related rows with a fixed number of extra SELECTs
(selectinload), so lists and detail pages never issue one query per product.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import Select, and_, case, false, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Category, Gender, Inventory, Product, ProductVariant


class SortOption(StrEnum):
    recommended = "recommended"
    price_asc = "price-asc"
    price_desc = "price-desc"
    rating = "rating"
    discount = "discount"


@dataclass(frozen=True)
class ProductFilters:
    category: str | None = None
    gender: Gender | None = None
    size: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    smart_fit: bool | None = None
    on_sale: bool | None = None
    in_stock: bool | None = None
    is_new: bool | None = None
    q: str | None = None
    sort: SortOption = SortOption.recommended


def _with_related(query: Select) -> Select:
    return query.options(
        joinedload(Product.category),
        selectinload(Product.images),
        selectinload(Product.variants).selectinload(ProductVariant.inventory),
    )


def _active_products() -> Select:
    return (
        select(Product)
        .join(Product.category)
        .where(Product.is_active.is_(True), Category.is_active.is_(True))
    )


GENDER_VALUES = {g.value for g in Gender}


def _escape_like(text: str) -> str:
    return re.sub(r"([\\%_])", r"\\\1", text)


def _search_condition(q: str):
    """Every word must match name, type, category, gender, colour or keywords.

    Words are bound parameters (never concatenated into SQL). Gender is matched
    exactly so "men" does not match "women"; "shoes" also matches "shoe".
    """
    conditions = []
    for word in re.findall(r"[a-z0-9]+", q.lower())[:8]:
        stem = word[:-1] if len(word) > 3 and word.endswith("s") else word
        pattern = f"%{_escape_like(stem)}%"
        color_match = (
            select(ProductVariant.id)
            .where(
                ProductVariant.product_id == Product.id,
                ProductVariant.color_name.ilike(pattern, escape="\\"),
            )
            .exists()
        )
        conditions.append(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.product_type.ilike(pattern, escape="\\"),
                Product.search_keywords.ilike(pattern, escape="\\"),
                Category.name.ilike(pattern, escape="\\"),
                Product.gender == word if word in GENDER_VALUES else false(),
                color_match,
            )
        )
    return and_(*conditions)


def _apply_filters(query: Select, f: ProductFilters) -> Select:
    if f.category:
        query = query.where(Category.slug == f.category)
    if f.gender == Gender.unisex:
        query = query.where(Product.gender == Gender.unisex)
    elif f.gender:
        # Men's and women's views include unisex items, as in the storefront.
        query = query.where(Product.gender.in_([f.gender, Gender.unisex]))
    if f.size:
        query = query.where(
            select(ProductVariant.id)
            .where(
                ProductVariant.product_id == Product.id,
                ProductVariant.is_active.is_(True),
                ProductVariant.size == f.size,
            )
            .exists()
        )
    if f.min_price is not None:
        query = query.where(Product.base_price >= f.min_price)
    if f.max_price is not None:
        query = query.where(Product.base_price <= f.max_price)
    if f.smart_fit is not None:
        query = query.where(Product.smart_fit.is_(f.smart_fit))
    if f.is_new is not None:
        query = query.where(Product.is_new.is_(f.is_new))
    if f.on_sale is not None:
        on_sale = and_(
            Product.compare_at_price.is_not(None),
            Product.compare_at_price > Product.base_price,
        )
        query = query.where(on_sale if f.on_sale else ~on_sale)
    if f.in_stock is not None:
        has_stock = (
            select(ProductVariant.id)
            .join(ProductVariant.inventory)
            .where(
                ProductVariant.product_id == Product.id,
                ProductVariant.is_active.is_(True),
                Inventory.on_hand - Inventory.reserved > 0,
            )
            .exists()
        )
        query = query.where(has_stock if f.in_stock else ~has_stock)
    if f.q and f.q.strip():
        query = query.where(_search_condition(f.q))
    return query


def _apply_sort(query: Select, sort: SortOption) -> Select:
    if sort == SortOption.price_asc:
        order = [Product.base_price.asc()]
    elif sort == SortOption.price_desc:
        order = [Product.base_price.desc()]
    elif sort == SortOption.rating:
        order = [Product.rating_average.desc(), Product.review_count.desc()]
    elif sort == SortOption.discount:
        discount = case(
            (
                Product.compare_at_price > Product.base_price,
                (Product.compare_at_price - Product.base_price) * 100.0 / Product.compare_at_price,
            ),
            else_=0,
        )
        order = [discount.desc()]
    else:
        # "Recommended" is a plain rule, not an algorithm: featured first, then catalog order.
        order = [Product.featured.desc()]
    # Product id as the final tie-breaker keeps pagination stable.
    return query.order_by(*order, Product.id.asc())


def list_categories(db: Session) -> list[Category]:
    return list(
        db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.id))
    )


def list_products(
    db: Session, filters: ProductFilters, limit: int, offset: int
) -> tuple[list[Product], int]:
    filtered = _apply_filters(_active_products(), filters)
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    page = _with_related(_apply_sort(filtered, filters.sort)).limit(limit).offset(offset)
    return list(db.scalars(page).unique()), total


def get_product(db: Session, slug: str) -> Product | None:
    query = _with_related(_active_products().where(Product.slug == slug))
    return db.scalars(query).unique().one_or_none()


# Rule-based demo similarity, not visual AI: same product type first, then
# closely related types, and only if nothing matched, the same category.
RELATED_TYPES = {
    "Hoodie": ["Sweatshirt", "Jacket"],
    "Sweatshirt": ["Hoodie"],
    "Jacket": ["Hoodie"],
}


def similar_products(db: Session, product: Product, limit: int = 4) -> list[Product]:
    candidates = _active_products().where(Product.id != product.id)
    related = RELATED_TYPES.get(product.product_type, [])
    priority = case(
        (Product.product_type == product.product_type, 0),
        (Product.product_type.in_(related), 1),
        else_=2,
    )
    query = (
        candidates.where(Product.product_type.in_([product.product_type, *related]))
        .order_by(priority, Product.featured.desc(), Product.id)
        .limit(limit)
    )
    results = list(db.scalars(_with_related(query)).unique())
    if not results:
        fallback = candidates.where(Product.category_id == product.category_id)
        results = list(
            db.scalars(_with_related(fallback.order_by(Product.id).limit(limit))).unique()
        )
    return results
