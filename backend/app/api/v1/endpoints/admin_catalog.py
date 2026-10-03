"""Admin: categories, products, variants and image metadata (ADMIN only)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, require_admin
from app.schemas.admin_catalog import (
    AdminCategory,
    AdminProductDetail,
    AdminProductList,
    CategoryCreate,
    CategoryUpdate,
    ImageCreate,
    ImageUpdate,
    ProductCreate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)
from app.schemas.catalog import ErrorResponse
from app.services import admin_catalog as catalog

# require_admin runs for every route here: 401 without a session, 403 for customers.
router = APIRouter(
    prefix="/admin",
    tags=["admin: catalog"],
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "authentication_required"},
        403: {"model": ErrorResponse, "description": "admin_required"},
    },
)

CONFLICT = {409: {"model": ErrorResponse, "description": "slug/sku/variant/image already exists"}}


@router.get("/categories", summary="All categories with product counts")
def list_categories(db: DbSession) -> list[AdminCategory]:
    return catalog.list_categories(db)


@router.post("/categories", status_code=status.HTTP_201_CREATED, responses=CONFLICT)
def create_category(data: CategoryCreate, db: DbSession) -> AdminCategory:
    category = catalog.create_category(db, data)
    db.commit()
    return catalog.category_summary(db, category.id)


@router.patch(
    "/categories/{category_id}",
    summary="Edit or (de)activate a category",
    description="An inactive category and its products disappear from the shop; "
    "nothing is deleted.",
    responses=CONFLICT,
)
def update_category(category_id: int, data: CategoryUpdate, db: DbSession) -> AdminCategory:
    catalog.update_category(db, category_id, data)
    db.commit()
    return catalog.category_summary(db, category_id)


@router.get("/products", summary="Products with stock figures")
def list_products(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100, description="Name, slug or SKU")] = None,
    category_id: int | None = None,
    status: Literal["active", "inactive"] | None = None,
    low_stock: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminProductList:
    items, total = catalog.list_products(
        db,
        q=q,
        category_id=category_id,
        status=status,
        low_stock=low_stock,
        limit=limit,
        offset=offset,
    )
    return AdminProductList(items=items, total=total, limit=limit, offset=offset)


@router.get("/products/{product_id}", summary="One product with variants, stock and images")
def read_product(product_id: int, db: DbSession) -> AdminProductDetail:
    return catalog.product_detail(db, product_id)


@router.post(
    "/products",
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    description="New products are inactive by default: add variants, stock and images, "
    "then activate.",
    responses=CONFLICT,
)
def create_product(data: ProductCreate, db: DbSession) -> AdminProductDetail:
    product = catalog.create_product(db, data)
    db.commit()
    return catalog.product_detail(db, product.id)


@router.patch(
    "/products/{product_id}",
    summary="Edit or (de)activate a product",
    description="Products are never deleted; is_active=false hides them from the shop.",
    responses=CONFLICT,
)
def update_product(product_id: int, data: ProductUpdate, db: DbSession) -> AdminProductDetail:
    catalog.update_product(db, product_id, data)
    db.commit()
    return catalog.product_detail(db, product_id)


@router.post(
    "/products/{product_id}/variants",
    status_code=status.HTTP_201_CREATED,
    summary="Add a colour/size variant (with starting stock)",
    responses=CONFLICT,
)
def create_variant(product_id: int, data: VariantCreate, db: DbSession) -> AdminProductDetail:
    catalog.create_variant(db, product_id, data)
    db.commit()
    return catalog.product_detail(db, product_id)


@router.patch(
    "/variants/{variant_id}",
    summary="Edit or (de)activate a variant",
    description="Variants are never deleted. Inactive variants can't be bought; past "
    "orders keep their own copy.",
    responses=CONFLICT,
)
def update_variant(variant_id: int, data: VariantUpdate, db: DbSession) -> AdminProductDetail:
    variant = catalog.update_variant(db, variant_id, data)
    db.commit()
    return catalog.product_detail(db, variant.product_id)


@router.post(
    "/products/{product_id}/images",
    status_code=status.HTTP_201_CREATED,
    summary="Add image metadata",
    description="image_path must point to a static file of the web app under "
    "/images/products/. No file is uploaded.",
    responses=CONFLICT,
)
def create_image(product_id: int, data: ImageCreate, db: DbSession) -> AdminProductDetail:
    catalog.create_image(db, product_id, data)
    db.commit()
    return catalog.product_detail(db, product_id)


@router.patch("/images/{image_id}", summary="Edit image metadata or position", responses=CONFLICT)
def update_image(image_id: int, data: ImageUpdate, db: DbSession) -> AdminProductDetail:
    image = catalog.update_image(db, image_id, data)
    db.commit()
    return catalog.product_detail(db, image.product_id)


@router.delete("/images/{image_id}", summary="Remove image metadata (the file stays)")
def delete_image(image_id: int, db: DbSession) -> AdminProductDetail:
    product_id = catalog.delete_image(db, image_id)
    db.commit()
    return catalog.product_detail(db, product_id)
