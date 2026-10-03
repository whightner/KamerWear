"""Pipeline check of the real OpenCLIP adapter (skipped without torch/open_clip).

Random weights are injected so no download is needed: this verifies the
adapter (preprocessing, tokenizer, batching, normalisation, CPU inference)
and measures its speed. It says nothing about search quality, which needs
the pretrained weights (python -m app.ai.prepare_visual_search).
"""

import time

import numpy as np
import pytest
from PIL import Image

open_clip = pytest.importorskip("open_clip")
pytest.importorskip("torch")

from app.ai.encoder import EncoderUnavailable, OpenClipEncoder  # noqa: E402


@pytest.fixture(scope="module")
def random_weight_encoder():
    real = open_clip.create_model_and_transforms

    def random_init(model, pretrained=None, **kwargs):
        assert pretrained == "laion2b_s34b_b79k"  # the adapter always asks for real weights
        return real(model, pretrained=None, **kwargs)

    open_clip.create_model_and_transforms = random_init
    try:
        yield OpenClipEncoder("ViT-B-32", "laion2b_s34b_b79k", "/nonexistent-cache", offline=True)
    finally:
        open_clip.create_model_and_transforms = real


def test_adapter_produces_normalised_512d_vectors(random_weight_encoder):
    images = [Image.new("RGB", (300, 400), (i * 40, 80, 120)) for i in range(5)]
    started = time.monotonic()
    vectors = random_weight_encoder.encode_images(images)
    seconds = time.monotonic() - started
    assert vectors.shape == (5, 512) and vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    texts = random_weight_encoder.encode_texts(["a photo of a sneaker", "a photo of a bag"])
    assert texts.shape == (2, 512)
    print(f"\nViT-B-32 on {random_weight_encoder.device}: {seconds / 5 * 1000:.0f} ms per image")


def test_missing_weights_raise_unavailable(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("403 Forbidden")

    monkeypatch.setattr(open_clip, "create_model_and_transforms", fail)
    with pytest.raises(EncoderUnavailable):
        OpenClipEncoder("ViT-B-32", "laion2b_s34b_b79k", "/nonexistent-cache", offline=True)
