from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.models import Gender, Product
from app.schemas.catalog import (
    ErrorResponse,
    ProductDetail,
    ProductListItem,
    ProductListResponse,
)
from app.services import catalog
from app.services.catalog import ProductFilters, SortOption

router = APIRouter(prefix="/products", tags=["catalog"])

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Unknown product slug"}}


def product_filters(
    category: Annotated[
        str | None,
        Query(max_length=80, pattern=SLUG_PATTERN, description="Category slug, e.g. `shoes`."),
    ] = None,
    gender: Annotated[
        Gender | None, Query(description="`men` and `women` also include unisex items.")
    ] = None,
    size: Annotated[str | None, Query(max_length=10, description="e.g. `M` or `43`.")] = None,
    min_price: Annotated[int | None, Query(ge=0, description="FCFA, inclusive.")] = None,
    max_price: Annotated[int | None, Query(ge=0, description="FCFA, inclusive.")] = None,
    smart_fit: bool | None = None,
    on_sale: Annotated[
        bool | None, Query(description="Has a compare-at price above the price.")
    ] = None,
    in_stock: bool | None = None,
    is_new: bool | None = None,
    q: Annotated[
        str | None,
        Query(
            max_length=80,
            description="Keywords matched against name, type, category, gender, colour.",
        ),
    ] = None,
    sort: SortOption = SortOption.recommended,
) -> ProductFilters:
    return ProductFilters(
        category=category,
        gender=gender,
        size=size,
        min_price=min_price,
        max_price=max_price,
        smart_fit=smart_fit,
        on_sale=on_sale,
        in_stock=in_stock,
        is_new=is_new,
        q=q,
        sort=sort,
    )


@router.get(
    "",
    summary="List products",
    description=(
        "Paginated, filterable product list. Filters combine with AND. "
        "`recommended` sorting is a plain rule (featured first, then catalog order)."
    ),
)
def list_products(
    db: DbSession,
    filters: Annotated[ProductFilters, Depends(product_filters)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductListResponse:
    products, total = catalog.list_products(db, filters, limit, offset)
    return ProductListResponse(
        items=[ProductListItem.model_validate(p) for p in products],
        total=total,
        limit=limit,
        offset=offset,
    )


def _get_or_404(db: Session, slug: str) -> Product:
    product = catalog.get_product(db, slug)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "product_not_found", "message": f"No product with slug '{slug}'."},
        )
    return product


SlugParam = Annotated[str, Path(max_length=120, examples=["urban-runner-02"])]


@router.get(
    "/{slug}",
    summary="Get product detail",
    description="Product with images, variants (effective price and stock) in one response.",
    responses=NOT_FOUND,
)
def get_product(slug: SlugParam, db: DbSession) -> ProductDetail:
    return ProductDetail.model_validate(_get_or_404(db, slug))


@router.get(
    "/{slug}/similar",
    summary="Find similar products (demo)",
    description=(
        "Rule-based demo similarity, not visual AI: same product type first, then "
        "closely related types (e.g. hoodies and jackets), else the same category."
    ),
    responses=NOT_FOUND,
)
def get_similar_products(
    slug: SlugParam,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=12)] = 4,
) -> list[ProductListItem]:
    product = _get_or_404(db, slug)
    return [ProductListItem.model_validate(p) for p in catalog.similar_products(db, product, limit)]
