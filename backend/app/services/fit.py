"""Smart Fit: photo estimates, the confirmed Fit Profile and size recommendations.

Privacy rules implemented here:
- Photos are only decoded in memory (EXIF dropped), analysed and discarded.
  They are never written to the database, disk or logs.
- An estimate stores derived numbers only; each customer keeps their last
  few, and deleting the Fit Profile deletes them too.
- Nothing becomes the Fit Profile until the customer confirms it (PUT).
"""

import logging
from dataclasses import dataclass

from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.images import load_upload
from app.ai.type_guard import product_group
from app.fit import charts, measure
from app.fit.measure import BodyEstimate, FitPhotoError
from app.fit.pose import PoseBackend
from app.models import FitEstimate, FitPreference, FitProfile, Product, User
from app.services.errors import ServiceError

logger = logging.getLogger(__name__)

ESTIMATION_VERSION = "kamerwear-fit-0.1"
KEEP_ESTIMATES = 3
# Photos are analysed at this size at most: enough detail, bounded CPU time.
MAX_ANALYSIS_SIDE = 1280
HEIGHT_RANGE = (100, 230)
MEASUREMENTS = ("shoulder_width_cm", "chest_cm", "waist_cm", "hip_cm", "inseam_cm")


def unavailable() -> ServiceError:
    return ServiceError(
        503,
        "fit_service_unavailable",
        "Photo sizing is unavailable right now. You can still choose your sizes yourself.",
    )


# --- Photos -------------------------------------------------------------------------


def load_photo(data: bytes, content_type: str | None, view: str) -> Image.Image:
    """Validated RGB copy without metadata, with Smart Fit error codes."""
    try:
        return load_upload(data, content_type)
    except ServiceError as exc:
        if exc.code == "image_too_large":
            raise ServiceError(
                413,
                "fit_image_too_large",
                f"The {view} photo is too large. {exc.message}",
                photo=view,
            ) from None
        raise ServiceError(
            400, "invalid_fit_image", f"The {view} photo can't be used. {exc.message}", photo=view
        ) from None


def analysis_copy(image: Image.Image) -> Image.Image:
    copy = image.copy()
    copy.thumbnail((MAX_ANALYSIS_SIDE, MAX_ANALYSIS_SIDE), Image.Resampling.LANCZOS)
    return copy


def _view(backend: PoseBackend, image: Image.Image, view: str) -> measure.View:
    warnings = measure.check_image(image, view)
    small = analysis_copy(image)
    try:
        result = backend.detect(small)
    finally:
        small.close()
    checked = measure.check_pose(result, view)
    checked.warnings = warnings + checked.warnings
    return checked


# --- Estimates ----------------------------------------------------------------------


def validate_height(value: object) -> int:
    try:
        height = int(str(value).strip())
    except (TypeError, ValueError):
        height = 0
    if not HEIGHT_RANGE[0] <= height <= HEIGHT_RANGE[1]:
        raise ServiceError(
            422,
            "invalid_fit_height",
            f"Enter your height in centimetres, between {HEIGHT_RANGE[0]} and {HEIGHT_RANGE[1]}.",
        )
    return height


def validate_preference(value: object) -> FitPreference:
    try:
        return FitPreference(str(value or "regular").strip().lower())
    except ValueError:
        raise ServiceError(
            422, "invalid_fit_preference", "Choose Slim, Regular or Relaxed."
        ) from None


@dataclass
class EstimateOutcome:
    row: FitEstimate
    body: BodyEstimate
    suggestions: dict[str, dict[str, str | None]]  # preference -> {"top": ..., "bottom": ...}
    notes: list[str]


def suggestions_for(measurements: dict, preference: str) -> tuple[dict, list[str]]:
    top = charts.suggest_top(measurements.get("chest_cm"), preference)
    bottom = charts.suggest_bottom(
        measurements.get("waist_cm"), measurements.get("hip_cm"), preference
    )
    notes = []
    if top and top.note:
        notes.append(f"Top: {top.note}")
    if bottom and bottom.note:
        notes.append(f"Trousers: {bottom.note}")
    return {"top": top.size if top else None, "bottom": bottom.size if bottom else None}, notes


def estimate(
    db: Session,
    user: User,
    backend: PoseBackend,
    front: Image.Image,
    side: Image.Image | None,
    height_cm: int,
    preference: FitPreference,
) -> EstimateOutcome:
    """Analyses the photos and stores the derived numbers for review (not the profile)."""
    try:
        front_view = _view(backend, front, "front")
        side_view = _view(backend, side, "side") if side is not None else None
    except FitPhotoError as exc:
        raise ServiceError(422, exc.code, exc.message, photo=exc.photo) from None
    body = measure.estimate(front_view, side_view, height_cm)

    suggestions, notes = {}, []
    for option in FitPreference:
        suggestions[option.value], option_notes = suggestions_for(body.measurements, option)
        if option == preference:
            notes = option_notes

    row = FitEstimate(
        user_id=user.id,
        height_cm=height_cm,
        fit_preference=preference,
        used_side_photo=body.used_side_photo,
        suggested_top_size=suggestions[preference]["top"],
        suggested_bottom_size=suggestions[preference]["bottom"],
        confidence=body.confidence,
        warnings=body.warnings,
        estimation_version=f"{ESTIMATION_VERSION}/{backend.model_name}",
        **body.measurements,
    )
    db.add(row)
    db.flush()
    _prune_estimates(db, user.id)
    db.commit()
    db.refresh(row)
    # Only counts and timing-free facts; never measurements or file details.
    logger.info("Smart Fit estimate %s (confidence %s)", row.id, row.confidence)
    return EstimateOutcome(row=row, body=body, suggestions=suggestions, notes=notes)


def _prune_estimates(db: Session, user_id: int) -> None:
    keep = select(FitEstimate.id).where(FitEstimate.user_id == user_id)
    keep = keep.order_by(FitEstimate.id.desc()).limit(KEEP_ESTIMATES)
    db.execute(
        delete(FitEstimate).where(FitEstimate.user_id == user_id, FitEstimate.id.not_in(keep))
    )


# --- Fit Profile --------------------------------------------------------------------


def get_profile(db: Session, user: User) -> FitProfile | None:
    return db.scalar(select(FitProfile).where(FitProfile.user_id == user.id))


def require_profile(db: Session, user: User) -> FitProfile:
    profile = get_profile(db, user)
    if profile is None:
        raise ServiceError(404, "fit_profile_not_found", "You don't have a Fit Profile yet.")
    return profile


@dataclass
class ProfileInput:
    height_cm: int
    fit_preference: FitPreference
    top_size: str | None
    bottom_size: str | None
    shoe_size_eu: int | None
    estimate_id: int | None = None


def save_profile(db: Session, user: User, data: ProfileInput) -> FitProfile:
    """Saves what the customer confirmed. Sizes they choose always win."""
    if data.top_size is not None and data.top_size not in charts.top_sizes():
        raise ServiceError(422, "invalid_fit_size", f"Unknown top size '{data.top_size}'.")
    if data.bottom_size is not None and data.bottom_size not in charts.bottom_sizes():
        raise ServiceError(422, "invalid_fit_size", f"Unknown trouser size '{data.bottom_size}'.")
    low, high = charts.shoe_range()
    if data.shoe_size_eu is not None and not low <= data.shoe_size_eu <= high:
        raise ServiceError(
            422, "invalid_fit_size", f"Enter an EU shoe size between {low} and {high}."
        )
    validate_height(data.height_cm)

    estimate_row = None
    if data.estimate_id is not None:
        estimate_row = db.get(FitEstimate, data.estimate_id)
        if estimate_row is None or estimate_row.user_id != user.id:
            raise ServiceError(
                404, "fit_estimate_not_found", "This estimate has expired. Please scan again."
            )
        if estimate_row.height_cm != data.height_cm:
            raise ServiceError(
                422,
                "fit_estimate_mismatch",
                "The height doesn't match the photos' estimate. Please scan again.",
            )

    profile = get_profile(db, user)
    previous_height = profile.height_cm if profile else None
    if profile is None:
        profile = FitProfile(user_id=user.id)

    if estimate_row is not None:
        # Measurements always come from the stored estimate, never from the client.
        for name in MEASUREMENTS:
            setattr(profile, f"estimated_{name}", getattr(estimate_row, name))
        measurements = {name: _float(getattr(estimate_row, name)) for name in MEASUREMENTS}
        suggested, _ = suggestions_for(measurements, data.fit_preference)
        corrected = (data.top_size, data.bottom_size) != (suggested["top"], suggested["bottom"])
        profile.source = "photo_corrected" if corrected else "photo_estimate"
        profile.confidence = estimate_row.confidence
        profile.estimation_version = estimate_row.estimation_version
    elif previous_height is not None and previous_height != data.height_cm:
        # Estimated dimensions were scaled to the old height: drop them.
        for name in MEASUREMENTS:
            setattr(profile, f"estimated_{name}", None)
        profile.source, profile.confidence, profile.estimation_version = "manual", None, None
    elif profile.source is None or profile.source == "manual":
        profile.source = "manual"
    elif (data.top_size, data.bottom_size) != (profile.top_size, profile.bottom_size):
        profile.source = "photo_corrected"

    profile.height_cm = data.height_cm
    profile.fit_preference = data.fit_preference
    profile.top_size = data.top_size
    profile.bottom_size = data.bottom_size
    profile.shoe_size_eu = data.shoe_size_eu
    profile.confirmed_by_user = True
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, user: User) -> None:
    """Removes the Fit Profile and every stored estimate (the account stays)."""
    db.execute(delete(FitProfile).where(FitProfile.user_id == user.id))
    db.execute(delete(FitEstimate).where(FitEstimate.user_id == user.id))
    db.commit()


def _float(value) -> float | None:
    return float(value) if value is not None else None


def profile_measurements(profile: FitProfile) -> dict[str, float | None]:
    return {name: _float(getattr(profile, f"estimated_{name}")) for name in MEASUREMENTS}


# --- Product recommendations --------------------------------------------------------


KIND_BY_GROUP = {"tops": "top", "outerwear": "top", "bottoms": "bottom", "footwear": "shoe"}


@dataclass
class Recommendation:
    status: str  # recommended, unavailable, not_offered, missing_size, no_profile, unsupported
    kind: str | None = None
    size: str | None = None
    size_label: str | None = None
    nearest_available: str | None = None
    source: str | None = None
    confidence: str | None = None
    message: str | None = None


def product_kind(product: Product) -> str | None:
    if not product.smart_fit or not product.sizes:
        return None
    return KIND_BY_GROUP.get(product_group(product.product_type, product.category.slug) or "")


def _label(kind: str, size: str) -> str:
    return f"EU {size}" if kind == "shoe" else size


def _profile_size(profile: FitProfile, kind: str, product_sizes: list[str]) -> str | None:
    if kind == "top":
        return profile.top_size
    if kind == "shoe":
        return str(profile.shoe_size_eu) if profile.shoe_size_eu is not None else None
    if profile.bottom_size is None:
        return None
    if all(size.isdigit() for size in product_sizes):
        return profile.bottom_size
    return charts.bottom_letter(profile.bottom_size)


def _scale(kind: str, sizes: list[str]) -> list[str]:
    """All sizes of this kind in order, to find the closest one."""
    if kind == "shoe" or all(size.isdigit() for size in sizes):
        return sorted(set(sizes), key=lambda s: float(s) if s.replace(".", "").isdigit() else 0)
    return charts.top_sizes()


def _nearest_in_stock(kind: str, wanted: str, product: Product) -> str | None:
    in_stock = list(dict.fromkeys(v.size for v in product.active_variants if v.size and v.in_stock))
    if not in_stock:
        return None
    scale = _scale(kind, product.sizes + [wanted])
    if wanted not in scale:
        return None
    position = scale.index(wanted)
    known = [size for size in in_stock if size in scale]
    if not known:
        return None
    # Closest first; on a tie, the larger size (easier to wear than too small).
    return min(known, key=lambda s: (abs(scale.index(s) - position), -scale.index(s)))


def recommend(product: Product, profile: FitProfile | None) -> Recommendation:
    """Never selects a variant or touches the cart: it only describes the match."""
    kind = product_kind(product)
    if kind is None:
        return Recommendation(status="unsupported")
    if profile is None:
        return Recommendation(
            status="no_profile",
            kind=kind,
            message="Create your Fit Profile to see your recommended size.",
        )
    base = {"kind": kind, "source": profile.source, "confidence": profile.confidence}
    size = _profile_size(profile, kind, product.sizes)
    if size is None:
        what = {"top": "top", "bottom": "trouser", "shoe": "shoe"}[kind]
        return Recommendation(
            status="missing_size",
            message=f"Add your {what} size to your Fit Profile to get a recommendation.",
            **base,
        )
    label = _label(kind, size)
    nearest = _nearest_in_stock(kind, size, product)
    nearest_label = _label(kind, nearest) if nearest else None
    if size not in product.sizes:
        message = f"This product doesn't come in your size ({label})."
        if nearest_label:
            message += f" Closest available size: {nearest_label}."
        return Recommendation(
            status="not_offered",
            size=size,
            size_label=label,
            nearest_available=nearest,
            message=message,
            **base,
        )
    if not any(v.size == size and v.in_stock for v in product.active_variants):
        message = f"Your usual size is {label}, but {label} is unavailable."
        if nearest_label:
            message += f" Closest available size: {nearest_label}."
        return Recommendation(
            status="unavailable",
            size=size,
            size_label=label,
            nearest_available=nearest,
            message=message,
            **base,
        )
    return Recommendation(status="recommended", size=size, size_label=label, **base)
