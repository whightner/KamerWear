"""Smart Fit: photo estimates, the customer's Fit Profile and product recommendations."""

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.ai.images import MAX_UPLOAD_BYTES
from app.api.deps import CurrentAuth, DbSession
from app.core import rate_limit
from app.fit import charts
from app.fit.pose import FitServiceUnavailable, get_backend
from app.models import FitProfile
from app.schemas.catalog import ErrorResponse
from app.schemas.fit import (
    FitEstimateResponse,
    FitMeasurements,
    FitProfileResponse,
    FitProfileUpdate,
    FitSuggestedSizes,
    ProductFitRecommendation,
)
from app.services import catalog
from app.services import fit as service
from app.services.errors import ServiceError

router = APIRouter(tags=["smart fit"])

# Two photos plus multipart overhead.
_MAX_BODY = 2 * MAX_UPLOAD_BYTES + 64 * 1024

AUTH_ERRORS = {401: {"model": ErrorResponse, "description": "authentication_required"}}
ESTIMATE_ERRORS = {
    **AUTH_ERRORS,
    400: {"model": ErrorResponse, "description": "invalid_fit_image"},
    413: {"model": ErrorResponse, "description": "fit_image_too_large"},
    422: {
        "model": ErrorResponse,
        "description": "fit_pose_not_detected / fit_full_body_not_visible / "
        "fit_multiple_people / fit_photo_quality / invalid_fit_height",
    },
    429: {"model": ErrorResponse, "description": "too_many_fit_estimates"},
    503: {"model": ErrorResponse, "description": "fit_service_unavailable"},
}


def _profile_response(profile: FitProfile) -> FitProfileResponse:
    return FitProfileResponse(
        height_cm=profile.height_cm,
        fit_preference=profile.fit_preference,
        top_size=profile.top_size,
        bottom_size=profile.bottom_size,
        bottom_size_letter=charts.bottom_letter(profile.bottom_size)
        if profile.bottom_size
        else None,
        shoe_size_eu=profile.shoe_size_eu,
        estimated_measurements=FitMeasurements(**service.profile_measurements(profile)),
        source=profile.source,
        confidence=profile.confidence,
        estimation_version=profile.estimation_version,
        confirmed_by_user=profile.confirmed_by_user,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def _read_photo(
    form, field: str, view: str, *, required: bool
) -> tuple[bytes, str | None] | None:
    upload = form.get(field)
    if not isinstance(upload, UploadFile) or (upload.size == 0 and not required):
        if required:
            raise ServiceError(400, "invalid_fit_image", "Add a front photo.", photo=view)
        return None
    return await upload.read(MAX_UPLOAD_BYTES + 1), upload.content_type


@router.post(
    "/fit/estimate",
    summary="Estimate sizes from a front (and optional side) photo",
    description="multipart/form-data: `front` (required) and `side` (optional) images "
    "(JPEG, PNG or WebP, max 8 MB each), `height_cm` (100-230) and `fit_preference` "
    "(slim, regular, relaxed). Photos are processed in memory and discarded. The result "
    "is only a suggestion: nothing is saved to the Fit Profile until PUT /fit/profile.",
    responses=ESTIMATE_ERRORS,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["front", "height_cm"],
                        "properties": {
                            "front": {"type": "string", "format": "binary"},
                            "side": {"type": "string", "format": "binary"},
                            "height_cm": {"type": "integer", "minimum": 100, "maximum": 230},
                            "fit_preference": {
                                "type": "string",
                                "enum": ["slim", "regular", "relaxed"],
                            },
                        },
                    }
                }
            },
        }
    },
)
async def estimate(request: Request, db: DbSession, current: CurrentAuth) -> FitEstimateResponse:
    key = str(current.user.id)
    if (wait := rate_limit.fit_estimates_by_user.retry_after(key)) is not None:
        raise ServiceError(
            429,
            "too_many_fit_estimates",
            "Too many photo estimates. Please wait a few minutes and try again.",
            retry_after=wait,
        )
    rate_limit.fit_estimates_by_user.hit(key)

    length = request.headers.get("content-length")
    if length is None or not length.isdigit():
        raise ServiceError(411, "invalid_fit_image", "Upload the photos as normal file uploads.")
    if int(length) > _MAX_BODY:
        raise ServiceError(
            413, "fit_image_too_large", "The photos are too large. Each must be under 8 MB."
        )

    form = await request.form(max_files=2, max_fields=4)
    try:
        height_cm = service.validate_height(form.get("height_cm"))
        preference = service.validate_preference(form.get("fit_preference"))
        front_data = await _read_photo(form, "front", "front", required=True)
        side_data = await _read_photo(form, "side", "side", required=False)
    finally:
        await form.close()  # deletes any temporary upload file straight away

    front = service.load_photo(*front_data, "front")
    side = service.load_photo(*side_data, "side") if side_data else None
    del front_data, side_data
    try:
        try:
            backend = await run_in_threadpool(get_backend)
        except FitServiceUnavailable:
            raise service.unavailable() from None
        try:
            outcome = await run_in_threadpool(
                service.estimate, db, current.user, backend, front, side, height_cm, preference
            )
        except ServiceError:
            raise
        except Exception:
            # Never show model internals to customers.
            raise service.unavailable() from None
    finally:
        front.close()
        if side is not None:
            side.close()

    row = outcome.row
    return FitEstimateResponse(
        estimate_id=row.id,
        height_cm=row.height_cm,
        fit_preference=row.fit_preference,
        used_side_photo=row.used_side_photo,
        measurements=FitMeasurements(**outcome.body.measurements),
        suggested=FitSuggestedSizes(**outcome.suggestions[preference]),
        suggested_by_preference={
            key: FitSuggestedSizes(**value) for key, value in outcome.suggestions.items()
        },
        size_notes=outcome.notes,
        confidence=outcome.body.confidence,
        confidence_factors=outcome.body.confidence_factors,
        warnings=outcome.body.warnings,
        estimation_version=row.estimation_version,
        size_chart_version=charts.chart_version(),
        created_at=row.created_at,
    )


@router.get(
    "/fit/profile",
    summary="The customer's confirmed Fit Profile",
    responses={
        **AUTH_ERRORS,
        404: {"model": ErrorResponse, "description": "fit_profile_not_found"},
    },
)
def get_profile(db: DbSession, current: CurrentAuth) -> FitProfileResponse:
    return _profile_response(service.require_profile(db, current.user))


@router.put(
    "/fit/profile",
    summary="Confirm or edit the Fit Profile",
    description="Saves the sizes the customer confirmed. With `estimate_id`, the estimated "
    "dimensions are copied from that estimate (it must be the customer's own); sizes the "
    "customer chose always win over suggestions.",
    responses={
        **AUTH_ERRORS,
        404: {"model": ErrorResponse, "description": "fit_estimate_not_found"},
        422: {"model": ErrorResponse, "description": "invalid_fit_size / fit_estimate_mismatch"},
    },
)
def save_profile(body: FitProfileUpdate, db: DbSession, current: CurrentAuth) -> FitProfileResponse:
    profile = service.save_profile(
        db,
        current.user,
        service.ProfileInput(
            height_cm=body.height_cm,
            fit_preference=body.fit_preference,
            top_size=body.top_size,
            bottom_size=body.bottom_size,
            shoe_size_eu=body.shoe_size_eu,
            estimate_id=body.estimate_id,
        ),
    )
    return _profile_response(profile)


@router.delete(
    "/fit/profile",
    status_code=204,
    summary="Delete the Fit Profile and stored estimates (keeps the account)",
    responses=AUTH_ERRORS,
)
def delete_profile(db: DbSession, current: CurrentAuth) -> Response:
    service.delete_profile(db, current.user)
    return Response(status_code=204)


@router.get(
    "/fit/size-charts",
    summary="The demo size charts used for suggestions",
    description="Generic, versioned demo charts (not a brand's official chart).",
)
def size_charts() -> dict:
    return charts.charts()


@router.get(
    "/products/{slug}/fit-recommendation",
    summary="The customer's recommended size for a product",
    description="Uses the confirmed Fit Profile and the product's real variants. It never "
    "selects a variant or changes the cart.",
    responses={**AUTH_ERRORS, 404: {"model": ErrorResponse, "description": "product_not_found"}},
)
def product_recommendation(
    slug: str, db: DbSession, current: CurrentAuth
) -> ProductFitRecommendation:
    product = catalog.get_product(db, slug)
    if product is None:
        raise ServiceError(404, "product_not_found", f"No product with slug '{slug}'.")
    result = service.recommend(product, service.get_profile(db, current.user))
    return ProductFitRecommendation(**result.__dict__)
