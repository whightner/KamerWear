from typing import Annotated

from fastapi import APIRouter, Header, Query, Response, status

from app.api.deps import CurrentAuth, DbSession
from app.schemas.catalog import ErrorResponse
from app.schemas.orders import OrderCreate, OrderDetail, OrderListResponse, OrderSummary
from app.services import orders

router = APIRouter(prefix="/orders", tags=["orders"])

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="A random value (e.g. a UUID) generated once per checkout. "
        "Repeating the request with the same key returns the same order.",
    ),
]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Place an order from my cart",
    description="Re-checks stock and prices, reserves stock, copies the address and lines "
    "into the order and empties the cart, all in one transaction. Returns 200 with the "
    "existing order when the Idempotency-Key was already used.",
    responses={
        400: {"model": ErrorResponse, "description": "cart_empty"},
        404: {"model": ErrorResponse, "description": "address_not_found"},
        409: {
            "model": ErrorResponse,
            "description": "insufficient_stock / quote_changed",
        },
    },
)
def create_order(
    data: OrderCreate,
    idempotency_key: IdempotencyKey,
    response: Response,
    current: CurrentAuth,
    db: DbSession,
) -> OrderDetail:
    try:
        order, created = orders.create_order(db, current.user, data, idempotency_key)
    except Exception:
        db.rollback()  # never keep a half-made order or reservation
        raise
    db.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    return orders.order_detail(orders.get_order(db, current.user, order.order_number))


@router.get("", summary="My orders, newest first")
def list_orders(
    current: CurrentAuth,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrderListResponse:
    items, total = orders.list_orders(db, current.user, limit, offset)
    return OrderListResponse(
        items=[OrderSummary.model_validate(o) for o in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{order_number}",
    summary="One of my orders, with its tracking timeline",
    description="Also used by order tracking. Another customer's order number returns 404.",
    responses={404: {"model": ErrorResponse, "description": "order_not_found"}},
)
def read_order(order_number: str, current: CurrentAuth, db: DbSession) -> OrderDetail:
    return orders.order_detail(orders.get_order(db, current.user, order_number))
