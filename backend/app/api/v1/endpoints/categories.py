from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.catalog import CategoryResponse
from app.services import catalog

router = APIRouter(prefix="/categories", tags=["catalog"])


@router.get("", summary="List active categories")
def list_categories(db: DbSession) -> list[CategoryResponse]:
    return [CategoryResponse.model_validate(c) for c in catalog.list_categories(db)]
