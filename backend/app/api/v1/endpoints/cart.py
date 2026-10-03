from fastapi import APIRouter

from app.api.deps import CurrentAuth, DbSession
from app.schemas.cart import (
    CartItemAdd,
    CartItemUpdate,
    CartMergeRequest,
    CartMergeResponse,
    CartResponse,
)
from app.schemas.catalog import ErrorResponse
from app.services import cart

router = APIRouter(prefix="/cart", tags=["cart"])

STOCK_ERRORS = {
    404: {
        "model": ErrorResponse,
        "description": "variant_not_found / cart_item_not_found",
    },
    409: {"model": ErrorResponse, "description": "insufficient_stock / quantity_limit"},
}


@router.get("", summary="My cart, with current prices and stock")
def read_cart(current: CurrentAuth, db: DbSession) -> CartResponse:
    return cart.read_cart(db, current.user)


@router.post(
    "/items",
    summary="Add a product variant",
    description="Adds to the existing line if the variant is already in the cart. "
    "The total quantity may not exceed available stock.",
    responses=STOCK_ERRORS,
)
def add_item(data: CartItemAdd, current: CurrentAuth, db: DbSession) -> CartResponse:
    cart.add_item(db, current.user, data)
    db.commit()
    return cart.read_cart(db, current.user)


@router.patch("/items/{item_id}", summary="Change a line's quantity", responses=STOCK_ERRORS)
def update_item(
    item_id: int, data: CartItemUpdate, current: CurrentAuth, db: DbSession
) -> CartResponse:
    cart.update_item(db, current.user, item_id, data.quantity)
    db.commit()
    return cart.read_cart(db, current.user)


@router.delete("/items/{item_id}", summary="Remove a line", responses=STOCK_ERRORS)
def remove_item(item_id: int, current: CurrentAuth, db: DbSession) -> CartResponse:
    cart.remove_item(db, current.user, item_id)
    db.commit()
    return cart.read_cart(db, current.user)


@router.delete("", summary="Empty my cart")
def clear_cart(current: CurrentAuth, db: DbSession) -> CartResponse:
    cart.clear_cart(db, current.user)
    db.commit()
    return cart.read_cart(db, current.user)


@router.post(
    "/merge",
    summary="Add a guest cart after login",
    description="Combines duplicate variants, never exceeds current stock, ignores "
    "unavailable items and uses catalog prices. Lists every line that changed.",
)
def merge_cart(data: CartMergeRequest, current: CurrentAuth, db: DbSession) -> CartMergeResponse:
    adjustments = cart.merge_items(db, current.user, data.items)
    db.commit()
    return CartMergeResponse(cart=cart.read_cart(db, current.user), adjustments=adjustments)
