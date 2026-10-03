"""Photo checks and body-dimension geometry on synthetic silhouettes."""

import math

import pytest
from PIL import Image

from app.fit import measure
from app.fit.measure import FitPhotoError
from app.fit.pose import PoseResult
from tests.fit import FRONT, SIDE, Body, synthetic_pose


def front(body: Body = FRONT) -> measure.View:
    return measure.check_pose(synthetic_pose(body), "front")


def side(body: Body = SIDE) -> measure.View:
    return measure.check_pose(synthetic_pose(body), "side")


def ellipse(width: float, depth: float) -> float:
    a, b = width / 2, depth / 2
    return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))


def test_scale_comes_from_the_typed_height():
    view = front()
    assert (view.top, view.floor) == (100, 900)
    assert view.cm_per_px(160) == pytest.approx(0.2)


def test_front_only_estimate_uses_widths_and_typical_depth():
    result = measure.estimate(front(), None, 160)
    m = result.measurements
    # 160 cm over 800 px = 0.2 cm per pixel.
    assert m["shoulder_width_cm"] == pytest.approx(32.0)
    assert m["chest_cm"] == pytest.approx(round(ellipse(34, 34 * 0.75) * 1.15, 1))
    assert m["waist_cm"] == pytest.approx(round(ellipse(30, 30 * 0.77) * 1.07, 1))
    assert m["hip_cm"] == pytest.approx(round(ellipse(36, 36 * 0.70) * 1.06, 1))
    assert m["inseam_cm"] == pytest.approx((900 - FRONT.crotch_y) * 0.2, abs=0.2)
    assert result.used_side_photo is False
    assert result.confidence == "low"  # always low without a side photo
    assert any("No side photo" in factor for factor in result.confidence_factors)


def test_measurements_scale_with_height():
    short = measure.estimate(front(), None, 150).measurements
    tall = measure.estimate(front(), None, 180).measurements
    for key in ("shoulder_width_cm", "chest_cm", "waist_cm", "hip_cm", "inseam_cm"):
        assert tall[key] == pytest.approx(short[key] * 180 / 150, rel=0.01)


def test_estimate_is_deterministic():
    first = measure.estimate(front(), side(), 172)
    second = measure.estimate(front(), side(), 172)
    assert first == second


def test_side_photo_supplies_the_depth_and_raises_confidence():
    result = measure.estimate(front(), side(), 160)
    m = result.measurements
    assert m["chest_cm"] == pytest.approx(round(ellipse(34, 24) * 1.15, 1))
    assert m["waist_cm"] == pytest.approx(round(ellipse(30, 22) * 1.07, 1))
    assert m["hip_cm"] == pytest.approx(round(ellipse(36, 24.8) * 1.06, 1))
    assert result.used_side_photo is True
    assert result.warnings == []
    assert result.confidence == "high"


def test_warnings_lower_confidence_below_high():
    blurry_side = side()
    blurry_side.warnings.append("The side photo looks blurry.")
    result = measure.estimate(front(), blurry_side, 160)
    assert result.confidence == "medium"


def test_arms_touching_the_body_leave_those_levels_out():
    result = measure.estimate(front(Body(arms="touching")), side(), 160)
    m = result.measurements
    assert m["chest_cm"] is None and m["waist_cm"] is None and m["hip_cm"] is None
    assert m["shoulder_width_cm"] is not None and m["inseam_cm"] is not None
    assert any("arms slightly away" in w for w in result.warnings)
    assert result.confidence == "low"


def test_legs_together_fall_back_to_a_typical_crotch_position():
    result = measure.estimate(front(Body(leg_gap=False)), None, 160)
    expected_crotch = FRONT.hip_y + measure.CROTCH_DROP * 800
    assert result.measurements["inseam_cm"] == pytest.approx((900 - expected_crotch) * 0.2, abs=0.2)
    assert any("Inseam estimated from" in f for f in result.confidence_factors)


def test_unrealistic_values_are_dropped_with_a_warning():
    # A 92 cm wide waist outline is far outside any plausible body.
    result = measure.estimate(front(Body(chest=330, waist=320, hip=330, arms="none")), None, 230)
    assert result.measurements["waist_cm"] is None
    assert any("waist estimate looked unrealistic" in w for w in result.warnings)


def test_side_depth_out_of_proportion_is_replaced_by_a_typical_depth():
    result = measure.estimate(front(), side(Body(chest=30, waist=110, hip=124, side=True)), 160)
    assert result.measurements["chest_cm"] == pytest.approx(round(ellipse(34, 25.5) * 1.15, 1))
    assert any("looked unusual at the chest" in w for w in result.warnings)


def test_front_and_side_that_disagree_are_flagged():
    other = synthetic_pose(SIDE)
    other.landmarks[[23, 24], 1] += 60  # hips much lower than in the front photo
    result = measure.estimate(front(), measure.check_pose(other, "side"), 160)
    assert any("don't match well" in w for w in result.warnings)
    assert result.confidence != "high"


# --- Photo checks --------------------------------------------------------------------


def test_no_person():
    with pytest.raises(FitPhotoError) as error:
        measure.check_pose(PoseResult(600, 1000, people=0), "front")
    assert error.value.code == "fit_pose_not_detected"


def test_more_than_one_person():
    result = synthetic_pose(FRONT)
    result.people = 2
    with pytest.raises(FitPhotoError) as error:
        measure.check_pose(result, "front")
    assert error.value.code == "fit_multiple_people"


@pytest.mark.parametrize(
    ("hidden", "message"),
    [
        ([27, 28], "feet"),
        ([0], "head"),
        ([11], "shoulders and hips"),
        ([23, 24], "shoulders and hips"),
    ],
)
def test_missing_landmarks_explain_what_to_fix(hidden, message):
    with pytest.raises(FitPhotoError) as error:
        front(Body(hide=hidden))
    assert error.value.code == "fit_full_body_not_visible"
    assert message in error.value.message
    assert error.value.photo == "front"


def test_feet_outside_the_frame_are_not_visible():
    result = synthetic_pose(Body(floor=1100))
    with pytest.raises(FitPhotoError) as error:
        measure.check_pose(result, "front")
    assert error.value.code == "fit_full_body_not_visible"


def test_head_cut_off_at_the_top():
    with pytest.raises(FitPhotoError) as error:
        front(Body(top=0, floor=800))
    assert "top of your head" in error.value.message


def test_person_too_small_in_the_frame():
    with pytest.raises(FitPhotoError) as error:
        front(Body(top=600, floor=880, chest=40, waist=35, hip=42, shoulder_joints=38))
    assert error.value.code == "fit_photo_quality"


def test_side_slot_with_a_front_view_is_refused():
    with pytest.raises(FitPhotoError) as error:
        measure.check_pose(synthetic_pose(FRONT), "side")
    assert error.value.code == "fit_photo_quality" and error.value.photo == "side"


def test_front_slot_with_a_side_view_is_refused():
    with pytest.raises(FitPhotoError) as error:
        measure.check_pose(synthetic_pose(SIDE), "front")
    assert "looks like a side view" in error.value.message


def test_tiny_and_dark_photos_are_refused_and_blur_is_a_warning():
    with pytest.raises(FitPhotoError) as error:
        measure.check_image(Image.new("RGB", (300, 500), (200, 200, 200)), "front")
    assert "too small" in error.value.message
    with pytest.raises(FitPhotoError) as error:
        measure.check_image(Image.new("RGB", (600, 1000), (10, 10, 10)), "side")
    assert "too dark" in error.value.message and error.value.photo == "side"
    # A flat grey image has no sharp edges at all.
    assert "blurry" in measure.check_image(Image.new("RGB", (600, 1000), (150,) * 3), "front")[0]
