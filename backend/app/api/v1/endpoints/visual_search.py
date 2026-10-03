"""Customer visual search and visual similarity (public, rate-limited)."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.ai.encoder import EncoderUnavailable, active_model_name, get_encoder
from app.ai.images import MAX_UPLOAD_BYTES, load_upload
from app.api.deps import DbSession, client_ip
from app.core import rate_limit
from app.schemas.catalog import ErrorResponse, ProductListItem
from app.schemas.visual_search import (
    VisualSearchItem,
    VisualSearchQuery,
    VisualSearchResponse,
    VisualSimilarResponse,
)
from app.services import catalog
from app.services import visual_search as service
from app.services.errors import ServiceError

router = APIRouter(tags=["visual search"])

# Multipart overhead allowed on top of the image itself.
_MAX_BODY = MAX_UPLOAD_BYTES + 64 * 1024

ERRORS = {
    400: {"model": ErrorResponse, "description": "invalid_image"},
    413: {"model": ErrorResponse, "description": "image_too_large"},
    415: {"model": ErrorResponse, "description": "unsupported_image_type"},
    429: {"model": ErrorResponse, "description": "too_many_searches"},
    503: {"model": ErrorResponse, "description": "visual_search_unavailable / not_ready"},
}


def _items(matches) -> list[VisualSearchItem]:
    return [
        VisualSearchItem(
            product=ProductListItem.model_validate(m.product),
            similarity_score=m.score,
            matched_image=m.matched_image,
            matches_predicted_type=m.in_predicted_type,
        )
        for m in matches
    ]


@router.post(
    "/visual-search",
    summary="Find products that look like an uploaded photo",
    description="multipart/form-data with one `image` file (JPEG, PNG or WebP, max 8 MB). "
    "The photo is processed in memory and not stored. Scores are cosine similarities from "
    "a pretrained image model, used for ranking only.",
    responses=ERRORS,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["image"],
                        "properties": {"image": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
)
async def visual_search(
    request: Request,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=24)] = 8,
) -> VisualSearchResponse:
    ip = client_ip(request)
    if (wait := rate_limit.visual_searches_by_ip.retry_after(ip)) is not None:
        raise ServiceError(
            429,
            "too_many_searches",
            "Too many image searches. Please wait a minute and try again.",
            retry_after=wait,
        )
    rate_limit.visual_searches_by_ip.hit(ip)

    # Refuse oversized bodies before parsing them.
    length = request.headers.get("content-length")
    if length is None or not length.isdigit():
        raise ServiceError(411, "invalid_image", "Upload the image as a normal file upload.")
    if int(length) > _MAX_BODY:
        raise ServiceError(
            413, "image_too_large", "The image is larger than 8 MB. Please use a smaller photo."
        )

    form = await request.form(max_files=1, max_fields=2)
    try:
        upload = form.get("image")
        if not isinstance(upload, UploadFile):
            raise ServiceError(400, "invalid_image", "Choose an image to search with.")
        data = await upload.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await form.close()  # deletes any temporary file straight away
    image = load_upload(data, upload.content_type)
    del data

    try:
        encoder = await run_in_threadpool(get_encoder)
    except EncoderUnavailable:
        raise service.unavailable() from None
    try:
        result = await run_in_threadpool(service.search_by_image, db, encoder, image, limit=limit)
    except ServiceError:
        raise
    except Exception:
        # Never show model internals to customers.
        raise service.unavailable() from None
    finally:
        image.close()

    return VisualSearchResponse(
        query=VisualSearchQuery(
            predicted_type=result.prediction.group if result.guard_applied else None,
            predicted_type_label=result.prediction.label if result.guard_applied else None,
            type_guard_applied=result.guard_applied,
            weak_matches=result.weak,
            model=result.model_name,
            search_ms=result.milliseconds,
        ),
        items=_items(result.matches),
    )


@router.get(
    "/products/{slug}/visual-similar",
    summary="Products that look similar (image embeddings)",
    description="Uses the product's indexed image embeddings; the product itself is excluded. "
    "Different from /similar, which uses catalog rules.",
    responses={
        404: {"model": ErrorResponse, "description": "product_not_found"},
        409: {"model": ErrorResponse, "description": "product_not_indexed"},
        503: {"model": ErrorResponse, "description": "visual_search_not_ready"},
    },
)
def visual_similar(
    slug: str, db: DbSession, limit: Annotated[int, Query(ge=1, le=12)] = 4
) -> VisualSimilarResponse:
    product = catalog.get_product(db, slug)
    if product is None:
        raise ServiceError(404, "product_not_found", f"No product with slug '{slug}'.")
    result = service.similar_to_product(db, active_model_name(), product, limit=limit)
    return VisualSimilarResponse(
        type_guard_applied=result.guard_applied,
        weak_matches=result.weak,
        model=result.model_name,
        items=_items(result.matches),
    )
