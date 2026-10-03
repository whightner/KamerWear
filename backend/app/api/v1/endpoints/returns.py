"""Customer returns: eligibility, request, list, detail and cancel.

The owner always comes from the access token; another customer's return or
order looks exactly like a missing one (404).
"""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAuth, DbSession
from app.core.config import RETURN_WINDOW_DAYS
from app.models import Order, ReturnRequest, ReturnStatus
from app.schemas.catalog import ErrorResponse
from app.schemas.returns import (
    ReturnableItem,
    ReturnCancel,
    ReturnCreate,
    ReturnDetail,
    ReturnEligibility,
    ReturnEvent,
    ReturnItemResponse,
    ReturnList,
    ReturnRef,
    ReturnSummary,
)
from app.services import returns as service

router = APIRouter(tags=["returns"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "return_not_found"}}


def item_fields(item) -> dict:
    line = item.order_item
    return {
        "id": item.id,
        "order_item_id": line.id,
        "product_name": line.product_name,
        "product_slug": line.product_slug,
        "sku": line.sku,
        "size": line.size,
        "color_name": line.color_name,
        "image_path": line.image_path,
        "unit_price": line.unit_price,
        "quantity": item.quantity,
        "line_value": line.unit_price * item.quantity,
        "reason": item.reason,
        "condition_note": item.condition_note,
    }


def summary_fields(request: ReturnRequest, order_number: str) -> dict:
    return {
        "return_number": request.return_number,
        "order_number": order_number,
        "status": request.status,
        "reason_summary": request.reason_summary,
        "item_count": request.item_count,
        "return_value": request.return_value,
        "created_at": request.created_at,
    }


def refund_note(request: ReturnRequest) -> str | None:
    return service.REFUND_NOTE if request.status == ReturnStatus.refunded else None


def customer_detail(request: ReturnRequest, order_number: str) -> ReturnDetail:
    return ReturnDetail(
        **summary_fields(request, order_number),
        customer_note=request.customer_note,
        updated_at=request.updated_at,
        resolved_at=request.resolved_at,
        refunded_amount=request.refunded_amount,
        refund_note=refund_note(request),
        can_cancel=request.status == ReturnStatus.requested,
        items=[ReturnItemResponse(**item_fields(item)) for item in request.items],
        # Internal staff notes are never included here.
        history=[
            ReturnEvent(status=e.status, note=e.customer_note, created_at=e.created_at)
            for e in request.status_history
        ],
    )


def eligibility_response(check: service.Eligibility) -> ReturnEligibility:
    return ReturnEligibility(
        order_number=check.order.order_number,
        eligible=check.eligible,
        code=check.code,
        message=check.message,
        delivered_at=check.delivered_at,
        return_deadline=check.deadline,
        window_days=RETURN_WINDOW_DAYS,
        items=[
            ReturnableItem(
                order_item_id=line.id,
                product_name=line.product_name,
                product_slug=line.product_slug,
                sku=line.sku,
                size=line.size,
                color_name=line.color_name,
                image_path=line.image_path,
                unit_price=line.unit_price,
                purchased_quantity=line.quantity,
                already_returned=check.returned.get(line.id, 0),
                returnable_quantity=max(0, line.quantity - check.returned.get(line.id, 0))
                if check.eligible or check.code == "return_quantity_exceeded"
                else 0,
            )
            for line in check.order.items
        ],
        returns=[
            ReturnRef(return_number=r.return_number, status=r.status, created_at=r.created_at)
            for r in check.returns
        ],
    )


@router.get(
    "/orders/{order_number}/return-eligibility",
    summary="Can this order (still) be returned, and how many of each item?",
    responses={404: {"model": ErrorResponse, "description": "order_not_found"}},
)
def read_eligibility(order_number: str, current: CurrentAuth, db: DbSession) -> ReturnEligibility:
    return eligibility_response(service.eligibility_for(db, current.user, order_number))


@router.post(
    "/returns",
    status_code=status.HTTP_201_CREATED,
    summary="Request a return for delivered items",
    description=f"Only delivered orders, within {RETURN_WINDOW_DAYS} days of delivery. "
    "Quantities are checked against the purchase minus earlier active returns. The value "
    "is calculated from the purchase-time prices (merchandise only).",
    responses={
        404: {"model": ErrorResponse, "description": "order_not_found"},
        409: {"model": ErrorResponse, "description": "return_not_eligible / return_window_expired"},
        422: {
            "model": ErrorResponse,
            "description": "return_quantity_exceeded / return_item_invalid",
        },
    },
)
def create_return(data: ReturnCreate, current: CurrentAuth, db: DbSession) -> ReturnDetail:
    try:
        request = service.create_return(
            db,
            current.user,
            data.order_number,
            [service.NewItem(i.order_item_id, i.quantity, i.reason, i.note) for i in data.items],
            data.customer_note,
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    request = service.get_return(db, current.user, request.return_number)
    return customer_detail(request, data.order_number.strip().upper())


@router.get("/returns", summary="My returns, newest first")
def list_returns(
    current: CurrentAuth,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReturnList:
    rows, total = service.list_returns(db, current.user, limit, offset)
    return ReturnList(
        items=[ReturnSummary(**summary_fields(r, n)) for r, n in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def _order_number(db, request: ReturnRequest) -> str:
    return db.get(Order, request.order_id).order_number


@router.get("/returns/{return_number}", summary="One of my returns", responses=NOT_FOUND)
def read_return(return_number: str, current: CurrentAuth, db: DbSession) -> ReturnDetail:
    request = service.get_return(db, current.user, return_number)
    return customer_detail(request, _order_number(db, request))


@router.post(
    "/returns/{return_number}/cancel",
    summary="Cancel my return request (only while it is still requested)",
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "invalid_return_transition"},
    },
)
def cancel_return(
    return_number: str, current: CurrentAuth, db: DbSession, data: ReturnCancel | None = None
) -> ReturnDetail:
    request = service.get_return(db, current.user, return_number)
    try:
        service.cancel(db, current.user, request, data.note if data else None)
    except Exception:
        db.rollback()
        raise
    db.commit()
    request = service.get_return(db, current.user, return_number)
    return customer_detail(request, _order_number(db, request))
