from fastapi import APIRouter

from app.core.config import SERVICE_NAME
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> HealthResponse:
    """Liveness check. It does not touch the database."""
    return HealthResponse(status="ok", service=SERVICE_NAME)
