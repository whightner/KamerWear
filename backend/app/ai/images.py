"""Image input handling for visual search.

Uploads: decoded fully in memory, never written to the database, public
folders or logs. Only JPEG, PNG and WebP are accepted, judged by the file
content (not the name). Pillow's decompression-bomb guard is tightened.
The returned image is a fresh pixel copy, so EXIF (including GPS location) is
dropped even from the in-memory copy.

Catalog images: resolved under VISUAL_SEARCH_IMAGE_ROOT only, so a stored
path can never point outside images/products/.
"""

import io
import re
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.services.errors import ServiceError

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 30_000_000  # e.g. 6000 x 5000
MAX_SIDE = 8000
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

# Anything bigger is refused by Pillow before decoding (decompression bombs).
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

_CATALOG_PATH = re.compile(r"^/images/products/[A-Za-z0-9._/-]+$")


def _error(code: str, message: str, status: int = 400) -> ServiceError:
    return ServiceError(status, code, message)


def load_upload(data: bytes, content_type: str | None) -> Image.Image:
    """Validates an uploaded image and returns an RGB copy without metadata."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise _error(
            "image_too_large", "The image is larger than 8 MB. Please use a smaller photo.", 413
        )
    if not data:
        raise _error("invalid_image", "The file is empty.")
    if content_type and content_type.lower() in {"image/heic", "image/heif"}:
        raise _error(
            "unsupported_image_type",
            "HEIC photos aren't supported yet. Please use JPEG, PNG or WebP.",
            415,
        )
    try:
        with warnings.catch_warnings():
            # Pillow only warns between the limit and twice the limit: refuse those too.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
        with image:
            if image.format not in ALLOWED_FORMATS:
                raise _error(
                    "unsupported_image_type",
                    "Please upload a JPEG, PNG or WebP image.",
                    415,
                )
            width, height = image.size
            if width * height > MAX_PIXELS or max(width, height) > MAX_SIDE:
                raise _error(
                    "image_too_large",
                    "The image dimensions are too large. Please use a smaller photo.",
                    413,
                )
            image.load()
            # Respect the phone's rotation, then copy the pixels only: the new
            # image carries no EXIF, GPS or other metadata.
            upright = ImageOps.exif_transpose(image).convert("RGB")
            return Image.frombytes("RGB", upright.size, upright.tobytes())
    except ServiceError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise _error(
            "image_too_large",
            "The image dimensions are too large. Please use a smaller photo.",
            413,
        ) from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise _error("invalid_image", "This file isn't a readable image.") from None


def catalog_image_path(image_path: str, root: Path | None = None) -> Path:
    """Filesystem path of a catalog image, guaranteed inside images/products/.

    Raises ValueError for anything else (traversal, absolute paths, URLs).
    """
    if not _CATALOG_PATH.fullmatch(image_path) or ".." in image_path or "//" in image_path:
        raise ValueError(f"Not a catalog image path: {image_path!r}")
    base = ((root or settings.visual_search_image_root) / "images" / "products").resolve()
    candidate = (base.parent.parent / image_path.lstrip("/")).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError(f"Image path escapes the image folder: {image_path!r}")
    return candidate


def open_catalog_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        return image.convert("RGB")
