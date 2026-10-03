"""Admin: dashboard overview, inventory and order fulfilment (ADMIN only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminUser, DbSession, require_admin
from app.core.config import LOW_STOCK_THRESHOLD
from app.models import OrderStatus, PaymentStatus
from app.schemas.admin_store import (
    AdminOrderDetail,
    AdminOrderList,
    InventoryList,
    InventoryRow,
    InventoryUpdate,
    OrderStatusChange,
    Overview,
    PaymentStatusChange,
)
from app.schemas.catalog import ErrorResponse
from app.services import admin_store as store
from app.services import orders as order_service

router = APIRouter(
    prefix="/admin",
    tags=["admin: store"],
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "authentication_required"},
        403: {"model": ErrorResponse, "description": "admin_required"},
    },
)


@router.get("/overview", summary="Dashboard figures")
def read_overview(db: DbSession) -> Overview:
    return store.overview(db)


@router.get(
    "/inventory",
    summary="Stock per variant",
    description=f"low_stock: 1–{LOW_STOCK_THRESHOLD} available; out_of_stock: 0 available. "
    "Inactive products/variants are hidden unless include_inactive=true.",
)
def list_inventory(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    product_id: int | None = None,
    low_stock: bool = False,
    out_of_stock: bool = False,
    include_inactive: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InventoryList:
    items, total = store.list_inventory(
        db,
        q=q,
        product_id=product_id,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return InventoryList(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        low_stock_threshold=LOW_STOCK_THRESHOLD,
    )


@router.patch(
    "/inventory/{variant_id}",
    summary="Set physical stock (on hand)",
    description="Only on_hand can be set; reserved belongs to orders. Rejected with "
    "inventory_below_reserved if on_hand would drop below reserved.",
    responses={409: {"model": ErrorResponse, "description": "inventory_below_reserved"}},
)
def update_inventory(variant_id: int, data: InventoryUpdate, db: DbSession) -> InventoryRow:
    store.set_on_hand(db, variant_id, data.on_hand)
    db.commit()
    return store.inventory_row(db, variant_id)


@router.get("/orders", summary="All orders, newest first")
def list_orders(
    db: DbSession,
    q: Annotated[
        str | None, Query(max_length=100, description="Order number, email, name or phone")
    ] = None,
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    city: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminOrderList:
    items, total = store.list_orders(
        db,
        q=q,
        status=status,
        payment_status=payment_status,
        city=city,
        limit=limit,
        offset=offset,
    )
    return AdminOrderList(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/orders/{order_number}",
    summary="Any order, with internal history and allowed next steps",
    responses={404: {"model": ErrorResponse, "description": "order_not_found"}},
)
def read_order(order_number: str, db: DbSession) -> AdminOrderDetail:
    return store.order_detail(db, store.get_order(db, order_number))


@router.post(
    "/orders/{order_number}/status",
    summary="Move an order to its next status",
    description="Follows the order state machine (see docs). Delivering or cancelling "
    "updates inventory once. `note` is shown to the customer; `internal_note` is not.",
    responses={409: {"model": ErrorResponse, "description": "invalid_order_transition"}},
)
def change_status(
    order_number: str, data: OrderStatusChange, admin: AdminUser, db: DbSession
) -> AdminOrderDetail:
    order = store.get_order(db, order_number)
    try:
        order_service.change_status(
            db, order, data.status, data.note, internal_note=data.internal_note, changed_by=admin
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    return store.order_detail(db, store.get_order(db, order_number))


@router.post(
    "/orders/{order_number}/payment-status",
    summary="Record a manual (demo) payment status",
    description="No payment provider is involved and no money moves.",
    responses={409: {"model": ErrorResponse, "description": "invalid_payment_transition"}},
)
def change_payment_status(
    order_number: str, data: PaymentStatusChange, admin: AdminUser, db: DbSession
) -> AdminOrderDetail:
    order = store.get_order(db, order_number)
    try:
        order_service.change_payment_status(
            db, order, data.payment_status, data.note, changed_by=admin
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    return store.order_detail(db, store.get_order(db, order_number))
