"""Admin: visual search index status and rebuild (ADMIN only)."""

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.ai.encoder import EncoderUnavailable, encoder_state, get_encoder
from app.api.deps import DbSession, require_admin
from app.schemas.catalog import ErrorResponse
from app.schemas.visual_search import IndexRunSummary, RebuildResult, VisualSearchStatus
from app.services import visual_search as service
from app.services.errors import ServiceError

router = APIRouter(
    prefix="/admin/visual-search",
    tags=["admin: visual search"],
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "authentication_required"},
        403: {"model": ErrorResponse, "description": "admin_required"},
    },
)


@router.get("/status", summary="Visual search index status")
def read_status(db: DbSession) -> VisualSearchStatus:
    status = service.index_status(db, encoder_state())
    run = status.last_run
    return VisualSearchStatus(
        model=status.model_name,
        encoder_state=status.encoder_state,
        ready=status.ready,
        active_images=status.active_images,
        indexed_images=status.indexed_images,
        products_represented=status.products_represented,
        active_products=status.active_products,
        stale_images=status.stale_images,
        unindexed_images=status.unindexed_images,
        missing_files=status.missing_files,
        last_run=IndexRunSummary(
            trigger=run.trigger,
            status=run.status,
            indexed=run.indexed,
            unchanged=run.unchanged,
            failed=run.failed,
            removed=run.removed,
            message=run.message,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        if run
        else None,
    )


@router.post(
    "/rebuild",
    summary="Index new or changed catalog images",
    description="Runs synchronously (seconds for the demo catalog). Only one build runs at a "
    "time (index_busy otherwise).",
    responses={
        409: {"model": ErrorResponse, "description": "index_busy"},
        503: {"model": ErrorResponse, "description": "visual_search_unavailable"},
    },
)
async def rebuild(db: DbSession) -> RebuildResult:
    try:
        encoder = await run_in_threadpool(get_encoder)
    except EncoderUnavailable:
        raise service.unavailable() from None
    try:
        report = await run_in_threadpool(service.build_index, db, encoder, trigger="admin")
    except service.IndexBusy:
        raise ServiceError(409, "index_busy", "An index build is already running.") from None
    return RebuildResult(
        model=report.model_name,
        indexed=report.indexed,
        unchanged=report.unchanged,
        failed=report.failed,
        removed=report.removed,
        seconds=report.seconds,
        problems=report.problems,
    )
