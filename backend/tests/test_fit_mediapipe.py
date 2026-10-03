"""Optional: the real MediaPipe pose model (skipped unless it is installed and prepared).

pip install -r requirements-smart-fit.txt && python -m app.ai.prepare_smart_fit
"""

import pytest
from PIL import Image

from app.core.config import BACKEND_DIR
from app.fit import measure
from app.fit.pose import FitServiceUnavailable, MediaPipeBackend, model_path

pytest.importorskip("mediapipe")
PHOTO = BACKEND_DIR.parent / "frontend" / "public" / "images" / "features" / "smart-fit.webp"


@pytest.fixture(scope="module")
def backend():
    try:
        return MediaPipeBackend(model_path())
    except FitServiceUnavailable as exc:
        pytest.skip(f"Smart Fit model not prepared: {exc}")


def test_real_model_finds_a_full_body(backend):
    with Image.open(PHOTO) as image:
        photo = image.convert("RGB")
    result = backend.detect(photo)
    assert result.people == 1
    assert result.landmarks.shape == (33, 3)
    assert result.mask.shape == (photo.height, photo.width)
    view = measure.check_pose(result, "front")
    estimate = measure.estimate(view, None, 175)
    assert 25 <= estimate.measurements["shoulder_width_cm"] <= 55
    assert estimate.confidence == "low"  # front photo only


def test_odd_widths_do_not_crash_the_model(backend):
    # mediapipe 1.0.1 aborted the process on some widths; the backend pads them.
    with Image.open(PHOTO) as image:
        photo = image.convert("RGB").crop((0, 0, 701, 970))
    result = backend.detect(photo)
    assert result.mask.shape == (970, 701)


def test_real_model_sees_nobody_in_an_empty_photo(backend):
    result = backend.detect(Image.new("RGB", (640, 960), (230, 230, 230)))
    assert result.people == 0
