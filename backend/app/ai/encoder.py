"""Image/text encoders for visual search.

The real encoder is a pretrained OpenCLIP model (ViT-B-32, LAION-2B weights).
KamerWear does not train it; it only uses it to turn images (and a few short
type prompts) into embedding vectors. torch and open_clip are optional
dependencies, imported only when the encoder is first needed, so the shop
runs without them.

Tests inject a deterministic fake through `set_encoder()`.
"""

import logging
import os
import threading
import time
from typing import Protocol

import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncoderUnavailable(Exception):
    """The model can't be used (packages missing, weights not downloaded...)."""


class ImageEncoder(Protocol):
    model_name: str
    dimensions: int

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        """(n, d) float32, each row L2-normalised."""

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        """(n, d) float32, each row L2-normalised."""


def normalise(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


def configured_model_name() -> str:
    return f"{settings.visual_search_model}/{settings.visual_search_pretrained}"


class OpenClipEncoder:
    """Pretrained OpenCLIP model on CPU (or GPU when one is available)."""

    def __init__(self, model: str, pretrained: str, cache_dir: str, offline: bool) -> None:
        if offline:
            # Use only weights already in the cache; never touch the network.
            os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            import open_clip
            import torch
        except ImportError as exc:
            raise EncoderUnavailable(
                "The visual search packages are not installed "
                "(pip install -r requirements-visual-search.txt)."
            ) from exc
        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            # pretrained is required: we never run the network with random weights.
            created = open_clip.create_model_and_transforms(
                model, pretrained=pretrained, cache_dir=cache_dir, device=self.device
            )
        except Exception as exc:  # download failures, missing cache, bad tag...
            raise EncoderUnavailable(
                f"The {model}/{pretrained} weights could not be loaded. Run "
                "`python -m app.ai.prepare_visual_search` with network access first."
            ) from exc
        self._model, _, self._preprocess = created
        self._model.eval()
        self._tokenizer = open_clip.get_tokenizer(model)
        self.model_name = f"{model}/{pretrained}"
        self.dimensions = int(self._model.visual.output_dim)

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        torch = self._torch
        batch = torch.stack([self._preprocess(image.convert("RGB")) for image in images])
        with torch.inference_mode():
            features = self._model.encode_image(batch.to(self.device))
        return normalise(features.float().cpu().numpy())

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        torch = self._torch
        with torch.inference_mode():
            features = self._model.encode_text(self._tokenizer(texts).to(self.device))
        return normalise(features.float().cpu().numpy())


_lock = threading.Lock()
_encoder: ImageEncoder | None = None
_failure: tuple[float, str] | None = None
_RETRY_AFTER_SECONDS = 60


def get_encoder() -> ImageEncoder:
    """The process-wide encoder, loaded once on first use.

    A load failure is remembered for a minute so every request doesn't retry
    an expensive (and failing) model load.
    """
    global _encoder, _failure
    if _encoder is not None:
        return _encoder
    with _lock:
        if _encoder is not None:
            return _encoder
        if _failure and time.monotonic() - _failure[0] < _RETRY_AFTER_SECONDS:
            raise EncoderUnavailable(_failure[1])
        started = time.monotonic()
        try:
            _encoder = OpenClipEncoder(
                settings.visual_search_model,
                settings.visual_search_pretrained,
                str(settings.visual_search_cache_dir),
                settings.visual_search_offline,
            )
        except EncoderUnavailable as exc:
            _failure = (time.monotonic(), str(exc))
            # Log the cause for developers; customers only see a generic message.
            logger.warning("Visual search model unavailable: %s (%s)", exc, exc.__cause__)
            raise
        logger.info(
            "Visual search model %s loaded in %.1fs",
            _encoder.model_name,
            time.monotonic() - started,
        )
        return _encoder


def active_model_name() -> str:
    """The model whose embeddings are used: the loaded encoder's, else the configured one."""
    return _encoder.model_name if _encoder is not None else configured_model_name()


def encoder_state() -> str:
    """ "loaded", "failed" or "not_loaded" (without trying to load)."""
    if _encoder is not None:
        return "loaded"
    return "failed" if _failure else "not_loaded"


def set_encoder(encoder: ImageEncoder | None) -> None:
    """Replace the encoder (tests). None resets to lazy loading."""
    global _encoder, _failure
    with _lock:
        _encoder = encoder
        _failure = None
