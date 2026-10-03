from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1.router import api_router
from app.core.config import API_V1_PREFIX, API_VERSION, PROJECT_NAME, SERVICE_NAME, settings

app = FastAPI(title=PROJECT_NAME, version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    """Identify the API and point to its docs."""
    return {
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
    }
