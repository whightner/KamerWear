"""Download (once) and verify the Smart Fit pose model before a demo.

    python -m app.ai.prepare_smart_fit            # download the pinned model, then self-test
    python -m app.ai.prepare_smart_fit --offline  # verify the local file only (no network)

The model file (~30 MB) is saved to SMART_FIT_MODEL_PATH (default
backend/.model-cache/smart-fit/, git-ignored) and checked against a pinned
SHA-256. The API itself never downloads anything.
"""

import argparse
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

from app.core.config import BACKEND_DIR
from app.fit import measure
from app.fit.pose import (
    MODEL_NAME,
    MODEL_SHA256,
    MODEL_URL,
    FitServiceUnavailable,
    MediaPipeBackend,
    file_sha256,
    model_path,
)

# A licensed full-body photo already in the repository (Sylius demo assets, MIT).
SELF_TEST_IMAGE = (
    BACKEND_DIR.parent / "frontend" / "public" / "images" / "features" / "smart-fit.webp"
)


def download(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_URL}")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, suffix=".part") as part:
        temporary = Path(part.name)
        try:
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
                shutil.copyfileobj(response, part)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    if file_sha256(temporary) != MODEL_SHA256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("The downloaded file doesn't match the pinned SHA-256; not using it.")
    temporary.chmod(0o644)
    temporary.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the Smart Fit pose model.")
    parser.add_argument("--offline", action="store_true", help="use the local file only")
    args = parser.parse_args(argv)

    path = model_path()
    print(f"Model: {MODEL_NAME}")
    print(f"File:  {path}")
    if not args.offline and not (path.is_file() and file_sha256(path) == MODEL_SHA256):
        try:
            download(path)
        except Exception as exc:
            print(f"Download failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    started = time.monotonic()
    try:
        backend = MediaPipeBackend(path)
    except FitServiceUnavailable as exc:
        print(f"Not ready: {exc}", file=sys.stderr)
        if exc.__cause__ is not None:
            print(f"  cause: {type(exc.__cause__).__name__}: {exc.__cause__}", file=sys.stderr)
        return 1
    loaded = time.monotonic() - started

    if not SELF_TEST_IMAGE.is_file():
        print(f"Loaded in {loaded:.1f}s (self-test image missing, inference not checked).")
        return 0
    with Image.open(SELF_TEST_IMAGE) as image:
        photo = image.convert("RGB")
    started = time.monotonic()
    result = backend.detect(photo)
    detected = time.monotonic() - started
    try:
        measure.check_pose(result, "front")
    except measure.FitPhotoError as exc:
        print(f"Self-test failed: {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    print(
        f"Ready: loaded in {loaded:.1f}s, one photo analysed in {detected * 1000:.0f} ms "
        "(full body found in the self-test photo)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
