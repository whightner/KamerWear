"""Pose estimation for Smart Fit.

The real backend is Google's pretrained MediaPipe Pose Landmarker (BlazePose
GHUM, "heavy" variant, Apache-2.0). KamerWear does not train it; it uses the
33 body landmarks and the person-segmentation mask it returns. mediapipe is an
optional dependency imported on first use, so the shop runs without it.

Everything after this module works on a plain `PoseResult` (pixel landmarks
and a mask), so tests inject a deterministic fake through `set_backend()`.
"""

import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Pinned model file (downloaded once by `python -m app.ai.prepare_smart_fit`).
MODEL_NAME = "mediapipe-pose-landmarker-heavy-float16-v1"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
)
MODEL_SHA256 = "64437af838a65d18e5ba7a0d39b465540069bc8aae8308de3e318aad31fcbc7b"

# BlazePose landmark indices used by Smart Fit.
NOSE = 0
LEFT_EAR, RIGHT_EAR = 7, 8
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_HEEL, RIGHT_HEEL = 29, 30
LEFT_FOOT, RIGHT_FOOT = 31, 32
LANDMARK_COUNT = 33


class FitServiceUnavailable(Exception):
    """The pose model can't be used (package missing, model not prepared...)."""


@dataclass
class PoseResult:
    """One photo's pose, in pixels. Never returned to clients."""

    width: int
    height: int
    people: int  # how many people the model found
    # (33, 3): x, y in pixels and visibility 0..1 of the main person; None if nobody.
    landmarks: np.ndarray | None = None
    # (height, width) person probability 0..1, or None.
    mask: np.ndarray | None = None


class PoseBackend(Protocol):
    model_name: str

    def detect(self, image: Image.Image) -> PoseResult: ...


def model_path() -> Path:
    return settings.smart_fit_model_path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MediaPipeBackend:
    """MediaPipe Pose Landmarker on CPU, loaded from the local model file only."""

    model_name = MODEL_NAME

    def __init__(self, path: Path) -> None:
        if not path.is_file():
            raise FitServiceUnavailable(
                f"The pose model file is missing ({path.name}). "
                "Run `python -m app.ai.prepare_smart_fit` first."
            )
        if file_sha256(path) != MODEL_SHA256:
            raise FitServiceUnavailable(
                "The pose model file doesn't match the pinned version. "
                "Run `python -m app.ai.prepare_smart_fit` again."
            )
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision
        except ImportError as exc:
            raise FitServiceUnavailable(
                "The Smart Fit package is not installed "
                "(pip install -r requirements-smart-fit.txt)."
            ) from exc
        except OSError as exc:  # e.g. libEGL missing on a minimal Linux
            raise FitServiceUnavailable(
                "mediapipe could not load its native library (see docs/architecture/smart-fit.md)."
            ) from exc
        self._mp = mp
        options = vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=2,  # to notice a second person in the photo
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            output_segmentation_masks=True,
        )
        try:
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            raise FitServiceUnavailable("The pose model could not be loaded.") from exc
        # One graph per process; calls are serialised.
        self._lock = threading.Lock()

    def detect(self, image: Image.Image) -> PoseResult:
        pixels = np.asarray(image.convert("RGB"), dtype=np.uint8)
        height, width = pixels.shape[:2]
        # mediapipe 1.0.1 aborts the whole process when it copies out a float
        # mask whose rows are padded (widths that aren't a multiple of 4), so
        # the photo is padded on the right with its edge pixels and the mask
        # is cropped back afterwards.
        padded_width = -(-width // 16) * 16
        if padded_width != width:
            pixels = np.pad(pixels, ((0, 0), (0, padded_width - width), (0, 0)), mode="edge")
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(pixels)
        )
        with self._lock:
            result = self._landmarker.detect(mp_image)
        poses = []
        for index, pose in enumerate(result.pose_landmarks):
            points = np.array(
                [(p.x * padded_width, p.y * height, p.visibility or 0.0) for p in pose],
                dtype=np.float64,
            )
            mask = None
            if result.segmentation_masks and index < len(result.segmentation_masks):
                full = result.segmentation_masks[index].numpy_view()
                mask = np.array(full, dtype=np.float32).reshape(height, padded_width)[:, :width]
            poses.append((points, mask))
        if not poses:
            return PoseResult(width=width, height=height, people=0)
        # Main person: the tallest clearly detected body.
        people = [p for p in poses if _is_person(p[0])] or poses[:1]
        points, mask = max(people, key=lambda p: np.ptp(p[0][:, 1]))
        return PoseResult(
            width=width, height=height, people=len(people), landmarks=points, mask=mask
        )


def _is_person(points: np.ndarray) -> bool:
    """A second pose only counts as a person when its torso is clearly visible."""
    torso = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]
    return float(points[torso, 2].mean()) >= 0.5


_lock = threading.Lock()
_backend: PoseBackend | None = None
_failure: tuple[float, str] | None = None
_RETRY_AFTER_SECONDS = 60


def get_backend() -> PoseBackend:
    """The process-wide pose backend, loaded once on first use.

    A load failure is remembered for a minute so every request doesn't retry.
    """
    global _backend, _failure
    if _backend is not None:
        return _backend
    with _lock:
        if _backend is not None:
            return _backend
        if _failure and time.monotonic() - _failure[0] < _RETRY_AFTER_SECONDS:
            raise FitServiceUnavailable(_failure[1])
        started = time.monotonic()
        try:
            _backend = MediaPipeBackend(model_path())
        except FitServiceUnavailable as exc:
            _failure = (time.monotonic(), str(exc))
            logger.warning("Smart Fit model unavailable: %s (%s)", exc, exc.__cause__)
            raise
        logger.info("Smart Fit pose model loaded in %.1fs", time.monotonic() - started)
        return _backend


def set_backend(backend: PoseBackend | None) -> None:
    """Replace the backend (tests). None resets to lazy loading."""
    global _backend, _failure
    with _lock:
        _backend = backend
        _failure = None
