"""Photo checks and body-dimension estimates from pose landmarks + silhouette.

Input: a `PoseResult` per photo (33 landmarks in pixels and the model's
person mask) and the height the customer typed. Output: approximate body
dimensions in cm, warnings and a confidence level. Nothing here sees the
photo itself, and nothing is stored.

Method (documented in docs/architecture/smart-fit.md):

1. Scale: the person's height in pixels (top of the head in the mask to the
   lowest heel/toe point) corresponds to the typed height, giving cm per pixel.
2. Widths (front photo): the silhouette's horizontal width at chest, waist and
   hip levels, placed between the shoulder and hip landmarks. A level is left
   out when an arm touches the body there (the width would include the arm).
3. Depths (side photo, optional): the silhouette's width at the same levels,
   using the side photo's own scale.
4. Circumference: perimeter of an ellipse with that width and depth
   (Ramanujan's formula) times a fixed shape factor, because a torso is fuller
   than an ellipse. Without a side photo, depth = width x a typical ratio and
   the confidence is always "low".
5. Inseam: crotch to floor. The crotch is where the gap between the legs
   starts, or a typical distance below the hip landmarks when no gap shows.

These are estimates for choosing a clothing size, not tailor measurements.
"""

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageStat

from app.fit import pose as lm
from app.fit.pose import PoseResult

MIN_SIDE_PX = 400
MIN_BRIGHTNESS = 40  # mean grey level 0-255
BLUR_THRESHOLD = 15.0  # variance of the Laplacian at 512 px; below = probably blurry
MIN_VISIBILITY = 0.5

# Levels as fractions of the shoulder-to-hip distance (from the shoulder line).
CHEST_LEVEL = 0.30
WAIST_BAND = (0.50, 0.80)  # the narrowest width in this band
HIP_BAND = (0.95, 1.35)  # the widest width in this band

# Crotch below the hip landmarks, as a share of body height: typical, and the
# furthest a visible leg gap may start to count as the crotch.
CROTCH_DROP = 0.05
CROTCH_MAX_DROP = 0.09

# Depth/width ratio assumed without a side photo (typical adult proportions).
TYPICAL_DEPTH_RATIO = {"chest": 0.75, "waist": 0.77, "hip": 0.70}
# A torso cross-section is fuller than an ellipse: approximate factors that make
# the ellipse reproduce typical published adult averages (e.g. ANSUR II).
SHAPE_FACTOR = {"chest": 1.15, "waist": 1.07, "hip": 1.06}
# A side photo depth outside this share of the width is treated as unreliable.
DEPTH_RATIO_RANGE = (0.45, 1.05)

PLAUSIBLE_CM = {
    "shoulder_width_cm": (25, 55),
    "chest_cm": (65, 160),
    "waist_cm": (50, 150),
    "hip_cm": (65, 160),
    "inseam_cm": (50, 100),
}
LABELS = {
    "shoulder_width_cm": "shoulder width",
    "chest_cm": "chest",
    "waist_cm": "waist",
    "hip_cm": "hips",
    "inseam_cm": "inseam",
}

ARMS = [
    (lm.LEFT_SHOULDER, 13, 15, 19),  # shoulder, elbow, wrist, index finger
    (lm.RIGHT_SHOULDER, 14, 16, 20),
]


class FitPhotoError(Exception):
    """A photo can't be used; the message tells the customer what to change."""

    def __init__(self, code: str, message: str, photo: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.photo = photo


def _name(view: str) -> str:
    return f"{view} photo"


# --- Photo-level checks (before the pose model) -------------------------------


def laplacian_variance(grey: Image.Image) -> float:
    """Sharpness: variance of the Laplacian (low values mean few sharp edges)."""
    g = np.asarray(grey, dtype=np.float64)
    lap = g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4 * g[1:-1, 1:-1]
    return float(lap.var())


def check_image(image: Image.Image, view: str) -> list[str]:
    """Size and light checks; returns warnings, raises for unusable photos."""
    if min(image.size) < MIN_SIDE_PX:
        raise FitPhotoError(
            "fit_photo_quality",
            f"The {_name(view)} is too small. Please use a photo at least "
            f"{MIN_SIDE_PX} pixels wide.",
            view,
        )
    grey = image.convert("L")
    grey.thumbnail((512, 512))
    if ImageStat.Stat(grey).mean[0] < MIN_BRIGHTNESS:
        raise FitPhotoError(
            "fit_photo_quality",
            f"The {_name(view)} is too dark. Please take it in good light.",
            view,
        )
    if laplacian_variance(grey) < BLUR_THRESHOLD:
        return [f"The {_name(view)} looks blurry. A sharper photo gives better results."]
    return []


# --- Pose-level checks ---------------------------------------------------------


@dataclass
class View:
    """One checked photo: where the body is, in pixels."""

    name: str
    pose: PoseResult
    top: float  # top of the head
    floor: float  # lowest heel/toe point
    shoulder_y: float
    hip_y: float
    shoulder_x: float
    hip_x: float
    visibility: float  # mean visibility of the key landmarks
    warnings: list[str] = field(default_factory=list)

    @property
    def body_px(self) -> float:
        return self.floor - self.top

    @property
    def torso(self) -> float:
        return self.hip_y - self.shoulder_y

    def cm_per_px(self, height_cm: int) -> float:
        return height_cm / self.body_px

    def y_at(self, fraction: float) -> float:
        return self.shoulder_y + fraction * self.torso

    def x_at(self, fraction: float) -> float:
        return self.shoulder_x + min(fraction, 1.0) * (self.hip_x - self.shoulder_x)


def _visible(points: np.ndarray, index: int, width: int, height: int) -> bool:
    x, y, visibility = points[index]
    return visibility >= MIN_VISIBILITY and 0 <= x < width and 0 <= y < height


def _pair(points, pair, width, height, *, both: bool) -> bool:
    seen = [_visible(points, i, width, height) for i in pair]
    return all(seen) if both else any(seen)


def check_pose(result: PoseResult, view: str) -> View:
    """Checks that exactly one full body is visible and locates it."""
    name = _name(view)
    if result.people == 0 or result.landmarks is None:
        raise FitPhotoError(
            "fit_pose_not_detected",
            f"We couldn't find a person in the {name}. Make sure your whole body is in "
            "the frame and the light is good.",
            view,
        )
    if result.people > 1:
        raise FitPhotoError(
            "fit_multiple_people",
            f"More than one person is visible in the {name}. Please take it with only "
            "you in the frame.",
            view,
        )
    points, width, height = result.landmarks, result.width, result.height
    front = view == "front"

    if not _visible(points, lm.NOSE, width, height):
        raise FitPhotoError(
            "fit_full_body_not_visible",
            f"Your head isn't fully visible in the {name}. Leave a little space above your head.",
            view,
        )
    shoulders = (lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER)
    hips = (lm.LEFT_HIP, lm.RIGHT_HIP)
    if not (
        _pair(points, shoulders, width, height, both=front)
        and _pair(points, hips, width, height, both=front)
    ):
        raise FitPhotoError(
            "fit_full_body_not_visible",
            f"Your shoulders and hips need to be visible in the {name}. Avoid bags or "
            "long coats that cover them.",
            view,
        )
    ankles = (lm.LEFT_ANKLE, lm.RIGHT_ANKLE)
    feet = (lm.LEFT_HEEL, lm.RIGHT_HEEL, lm.LEFT_FOOT, lm.RIGHT_FOOT)
    if not _pair(points, ankles, width, height, both=front) or not any(
        _visible(points, i, width, height) for i in feet
    ):
        raise FitPhotoError(
            "fit_full_body_not_visible",
            f"Your feet aren't fully visible in the {name}. Step back or hold the phone "
            "lower so your whole body, head to feet, is in the frame.",
            view,
        )

    def mean(indices, axis):
        chosen = [i for i in indices if points[i, 2] >= MIN_VISIBILITY] or list(indices)
        return float(points[chosen, axis].mean())

    shoulder_y, hip_y = mean(shoulders, 1), mean(hips, 1)
    torso = hip_y - shoulder_y
    if torso <= 0:
        raise FitPhotoError(
            "fit_pose_not_detected",
            f"Please stand upright in the {name}.",
            view,
        )

    warnings: list[str] = []
    spread = abs(points[lm.LEFT_SHOULDER, 0] - points[lm.RIGHT_SHOULDER, 0]) / torso
    if front and spread < 0.40:
        raise FitPhotoError(
            "fit_photo_quality",
            "The front photo looks like a side view. Please face the camera.",
            view,
        )
    if front and spread < 0.50:
        warnings.append("You seem turned slightly in the front photo. Face the camera squarely.")
    if not front and spread > 0.45:
        raise FitPhotoError(
            "fit_photo_quality",
            "The side photo looks like a front view. Turn 90 degrees so your side faces "
            "the camera.",
            view,
        )

    foot_y = max(points[i, 1] for i in feet if points[i, 2] >= 0.3)
    nose_y = points[lm.NOSE, 1]
    head_x = float(np.mean(points[[lm.NOSE, lm.LEFT_EAR, lm.RIGHT_EAR], 0]))
    mask = result.mask
    if mask is not None:
        half = max(0.25 * torso, 4)
        left, right = int(max(0, head_x - half)), int(min(width, head_x + half + 1))
        rows = np.flatnonzero((mask[:, left:right] > 0.5).any(axis=1))
        rows = rows[rows < nose_y]
        if rows.size == 0:
            top = nose_y - 0.5 * (shoulder_y - nose_y)
        elif rows[0] <= 1:
            raise FitPhotoError(
                "fit_full_body_not_visible",
                f"The top of your head is cut off in the {name}. Leave a little space "
                "above your head.",
                view,
            )
        else:
            top = float(rows[0])
        # The mask may reach a little lower than the heel landmark (soles).
        xs = [points[i, 0] for i in feet]
        left, right = int(max(0, min(xs) - half)), int(min(width, max(xs) + half + 1))
        rows = np.flatnonzero((mask[:, left:right] > 0.5).any(axis=1))
        floor = float(foot_y)
        if rows.size:
            floor = float(min(max(rows[-1], foot_y), foot_y + 0.025 * (foot_y - top)))
    else:
        top = nose_y - 0.5 * (shoulder_y - nose_y)
        floor = float(foot_y)
        warnings.append(f"No body outline was available for the {name}.")

    body = floor - top
    if body < 0.30 * height:
        raise FitPhotoError(
            "fit_photo_quality",
            f"You're too far from the camera in the {name}. Move closer so your body "
            "fills most of the frame.",
            view,
        )
    if body < 0.50 * height:
        warnings.append(f"Move a little closer for the {name}, so your body fills more of it.")

    key = [lm.NOSE, *shoulders, *hips, *ankles]
    if front:
        visibility = float(points[key, 2].mean())
    else:  # only the near side is expected to be visible
        pairs = [shoulders, hips, ankles]
        visibility = float(
            np.mean([points[lm.NOSE, 2]] + [max(points[a, 2], points[b, 2]) for a, b in pairs])
        )
    if visibility < 0.65:
        warnings.append(f"Some body points were hard to see in the {name}.")

    return View(
        name=view,
        pose=result,
        top=top,
        floor=floor,
        shoulder_y=shoulder_y,
        hip_y=hip_y,
        shoulder_x=mean(shoulders, 0),
        hip_x=mean(hips, 0),
        visibility=visibility,
        warnings=warnings,
    )


# --- Silhouette geometry ---------------------------------------------------------


def silhouette_run(mask: np.ndarray, y: float, x: float) -> tuple[int, int] | None:
    """The continuous body segment of mask row y that contains column x."""
    row_index, column = int(round(y)), int(round(x))
    height, width = mask.shape
    if not (0 <= row_index < height and 0 <= column < width):
        return None
    row = mask[row_index] > 0.5
    if not row[column]:
        return None
    gaps = np.flatnonzero(~row)
    before, after = gaps[gaps < column], gaps[gaps > column]
    left = int(before[-1]) + 1 if before.size else 0
    right = int(after[0]) - 1 if after.size else width - 1
    return left, right


def arm_inside(points: np.ndarray, y: float, left: int, right: int) -> bool:
    """True when an arm (or hand) crosses row y inside the measured segment."""
    for chain in ARMS:
        joints = [points[i] for i in chain]
        wrist, index = joints[-2], joints[-1]
        # The fingers reach past the index landmark: extend the hand a little.
        joints.append(np.array([*(index[:2] + 0.8 * (index[:2] - wrist[:2])), index[2]]))
        for (xa, ya, va), (xb, yb, vb) in zip(joints, joints[1:], strict=False):
            if min(va, vb) < 0.3 or not (min(ya, yb) <= y <= max(ya, yb)) or ya == yb:
                continue
            x = xa + (y - ya) / (yb - ya) * (xb - xa)
            if left <= x <= right:
                return True
    return False


@dataclass
class Level:
    fraction: float
    width_px: float | None
    arm_blocked: bool = False


def _width(view: View, fraction: float, *, check_arms: bool) -> Level:
    mask, points = view.pose.mask, view.pose.landmarks
    y = view.y_at(fraction)
    run = silhouette_run(mask, y, view.x_at(fraction)) if mask is not None else None
    if run is None:
        return Level(fraction, None)
    if check_arms and arm_inside(points, y, *run):
        return Level(fraction, None, arm_blocked=True)
    return Level(fraction, float(run[1] - run[0] + 1))


def _band(view, band, *, widest: bool, check_arms: bool, steps: int = 9) -> Level:
    levels = [_width(view, f, check_arms=check_arms) for f in np.linspace(*band, steps)]
    usable = [level for level in levels if level.width_px]
    blocked = sum(level.arm_blocked for level in levels)
    if not usable or blocked > steps // 2:
        return Level(band[0], None, arm_blocked=blocked > 0)
    pick = max if widest else min
    return pick(usable, key=lambda level: level.width_px)


def _crotch_y(view: View) -> tuple[float, bool]:
    """Crotch height in pixels, and whether it was measured from the photo.

    Measured: the first row below the hips where the gap between the legs
    starts, if that is where a crotch can plausibly be. Loose trousers, shorts
    or legs held together hide the real gap, so otherwise it is placed at a
    typical distance below the hip landmarks.
    """
    mask = view.pose.mask
    expected = view.hip_y + CROTCH_DROP * view.body_px
    if mask is None:
        return expected, False
    x = int(round(view.hip_x))
    start = int(view.hip_y)
    stop = int(min(view.hip_y + CROTCH_MAX_DROP * view.body_px, mask.shape[0] - 1))
    if 0 <= x < mask.shape[1]:
        for y in range(start, stop + 1):
            if mask[y, x] <= 0.5:
                return float(y), True
    return expected, False


def ellipse_perimeter(width: float, depth: float) -> float:
    """Ramanujan's approximation for an ellipse with these full axes."""
    a, b = width / 2, depth / 2
    return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))


# --- The estimate -----------------------------------------------------------------


@dataclass
class BodyEstimate:
    measurements: dict[str, float | None]
    used_side_photo: bool
    confidence: str  # "high", "medium" or "low"
    confidence_factors: list[str]
    warnings: list[str]


def estimate(front: View, side: View | None, height_cm: int) -> BodyEstimate:
    warnings = list(front.warnings) + (list(side.warnings) if side else [])
    factors: list[str] = []
    points = front.pose.landmarks
    scale = front.cm_per_px(height_cm)

    shoulder_px = math.dist(points[lm.LEFT_SHOULDER, :2], points[lm.RIGHT_SHOULDER, :2])
    widths = {
        "chest": _width(front, CHEST_LEVEL, check_arms=True),
        "waist": _band(front, WAIST_BAND, widest=False, check_arms=True),
        "hip": _band(front, HIP_BAND, widest=True, check_arms=True),
    }
    chest = widths["chest"]
    if chest.width_px and chest.width_px > 1.6 * shoulder_px:  # still includes the arms
        widths["chest"] = Level(chest.fraction, None, arm_blocked=True)
    blocked = [name for name, level in widths.items() if level.arm_blocked]
    if blocked:
        warnings.append(
            "Your arms were touching your body at the "
            + " and ".join(LABELS[f"{name}_cm"] for name in blocked)
            + ", so we couldn't measure there. Hold your arms slightly away from your body."
        )

    depths: dict[str, float | None] = {}
    if side is not None:
        side_scale = side.cm_per_px(height_cm)
        side_levels = {
            "chest": _width(side, CHEST_LEVEL, check_arms=False),
            "waist": _width(side, widths["waist"].fraction, check_arms=False),
            "hip": _band(side, HIP_BAND, widest=True, check_arms=False),
        }
        unusual = []
        for name, level in side_levels.items():
            width = widths[name].width_px
            if level.width_px is None or width is None:
                depths[name] = None
                continue
            depth_cm, width_cm = level.width_px * side_scale, width * scale
            if DEPTH_RATIO_RANGE[0] <= depth_cm / width_cm <= DEPTH_RATIO_RANGE[1]:
                depths[name] = depth_cm
            else:
                depths[name] = None
                unusual.append(LABELS[f"{name}_cm"])
        if unusual:
            warnings.append(
                "The side photo's outline looked unusual at the "
                + " and ".join(unusual)
                + "; a typical body depth was used there."
            )
        factors.append("Side photo used to measure body depth.")
    else:
        factors.append(
            "No side photo: body depth was assumed from typical proportions, so confidence is low."
        )

    measurements: dict[str, float | None] = {
        "shoulder_width_cm": shoulder_px * scale,
        "chest_cm": None,
        "waist_cm": None,
        "hip_cm": None,
        "inseam_cm": None,
    }
    for name, level in widths.items():
        if level.width_px is None:
            continue
        width_cm = level.width_px * scale
        depth_cm = depths.get(name) or width_cm * TYPICAL_DEPTH_RATIO[name]
        measurements[f"{name}_cm"] = ellipse_perimeter(width_cm, depth_cm) * SHAPE_FACTOR[name]

    crotch, measured = _crotch_y(front)
    measurements["inseam_cm"] = (front.floor - crotch) * scale
    if not measured:
        factors.append(
            "Inseam estimated from your hip and foot positions (the gap between your legs "
            "wasn't visible)."
        )

    for key, value in measurements.items():
        low, high = PLAUSIBLE_CM[key]
        if value is not None and not low <= value <= high:
            measurements[key] = None
            warnings.append(f"The {LABELS[key]} estimate looked unrealistic and was left out.")
    measurements = {k: (round(v, 1) if v is not None else None) for k, v in measurements.items()}

    inconsistent = False
    if side is not None:
        front_legs = (front.floor - front.hip_y) / front.body_px
        side_legs = (side.floor - side.hip_y) / side.body_px
        if abs(front_legs - side_legs) > 0.05:
            inconsistent = True
            warnings.append(
                "The front and side photos don't match well (different pose or camera "
                "angle). Retaking them the same way gives more reliable results."
            )

    level, more = _confidence(front, side, measurements, warnings, inconsistent)
    return BodyEstimate(
        measurements=measurements,
        used_side_photo=side is not None,
        confidence=level,
        confidence_factors=factors + more,
        warnings=warnings,
    )


def _confidence(front, side, measurements, warnings, inconsistent) -> tuple[str, list[str]]:
    """A rule-based level, not a probability and not an accuracy figure."""
    factors = []
    visibility = front.visibility if side is None else (front.visibility + side.visibility) / 2
    factors.append(
        "Key body points were clearly visible."
        if visibility >= 0.8
        else "Some key body points were hard to see."
    )
    missing = [k for k in ("chest_cm", "waist_cm", "hip_cm") if measurements[k] is None]
    if missing:
        factors.append(
            "Not estimated: " + ", ".join(LABELS[k] for k in missing) + " (choose sizes yourself)."
        )
    if inconsistent:
        factors.append("Front and side photos disagree.")

    score = visibility - 0.05 * len(warnings) - 0.1 * len(missing) - (0.15 if inconsistent else 0)
    if side is None:
        return "low", factors
    if score >= 0.8 and not missing and not warnings:
        return "high", factors
    if score >= 0.6:
        return "medium", factors
    return "low", factors
