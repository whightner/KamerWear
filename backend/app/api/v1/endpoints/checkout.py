from fastapi import APIRouter

from app.api.deps import CurrentAuth, DbSession
from app.schemas.catalog import ErrorResponse
from app.schemas.orders import QuoteRequest, QuoteResponse
from app.services import orders

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post(
    "/quote",
    summary="Server-calculated checkout summary",
    description="Totals for the signed-in customer's cart, the chosen address and payment "
    "method. Lists anything that blocks ordering in `issues`. Changes nothing.",
    responses={404: {"model": ErrorResponse, "description": "address_not_found"}},
)
def checkout_quote(data: QuoteRequest, current: CurrentAuth, db: DbSession) -> QuoteResponse:
    return orders.quote(db, current.user, data.address_id, data.payment_method)
