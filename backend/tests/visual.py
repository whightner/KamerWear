"""Deterministic stand-ins for the vision model in visual search tests.

FakeEncoder embeds an image as its normalised mean colour. Catalog images are
replaced (in a temporary image root) by solid colours that depend on the
product's type group, slightly varied per product, so rankings and the type
guard can be checked exactly without a neural network.
"""

import io

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import select

from app.ai import encoder as encoder_module
from app.ai.type_guard import TYPE_GROUPS, product_group
from app.core.config import settings
from app.models import Category, Product, ProductImage
from app.services import visual_search

GROUP_COLORS = {
    "footwear": (220, 30, 30),
    "bags": (30, 30, 220),
    "outerwear": (30, 200, 30),
    "tops": (230, 220, 30),
    "bottoms": (150, 30, 160),
    "other": (128, 128, 128),
    None: (90, 160, 160),
}


def product_color(group: str | None, product_id: int) -> tuple[int, int, int]:
    base = GROUP_COLORS[group]
    shift = (product_id * 7) % 25
    return tuple(min(255, max(0, c + shift - 12)) for c in base)


class FakeEncoder:
    model_name = "fake/mean-colour"
    dimensions = 4

    def __init__(self) -> None:
        self.calls = 0

    def _vector(self, rgb) -> np.ndarray:
        r, g, b = np.asarray(rgb, dtype=np.float32) / 255.0
        return np.array([r, g, b, 0.05], dtype=np.float32)

    def encode_images(self, images):
        self.calls += 1
        vectors = [
            self._vector(np.asarray(img.convert("RGB")).reshape(-1, 3).mean(axis=0))
            for img in images
        ]
        return encoder_module.normalise(np.vstack(vectors))

    def encode_texts(self, texts):
        lookup = {p: g for g, (_, prompts) in TYPE_GROUPS.items() for p in prompts}
        return encoder_module.normalise(
            np.vstack([self._vector(GROUP_COLORS[lookup[t]]) for t in texts])
        )


def image_bytes(color=(220, 30, 30), size=(64, 64), fmt="JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


def write_catalog_images(db, root) -> dict[int, tuple[int, int, int]]:
    """Solid-colour stand-ins for every catalog image. Returns product_id -> colour."""
    colors = {}
    rows = db.execute(
        select(ProductImage.image_path, Product.id, Product.product_type, Category.slug)
        .join(Product, Product.id == ProductImage.product_id)
        .join(Category, Category.id == Product.category_id)
    ).all()
    for path, product_id, ptype, slug in rows:
        color = product_color(product_group(ptype, slug), product_id)
        colors[product_id] = color
        target = root / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 32), color).save(target, format="WEBP")
    return colors


@pytest.fixture
def fake_encoder():
    fake = FakeEncoder()
    encoder_module.set_encoder(fake)
    visual_search.reset_type_guard_cache()
    yield fake
    encoder_module.set_encoder(None)
    visual_search.reset_type_guard_cache()


@pytest.fixture
def image_root(tmp_path, monkeypatch, db_session):
    monkeypatch.setattr(settings, "visual_search_image_root", tmp_path)
    colors = write_catalog_images(db_session, tmp_path)
    return tmp_path, colors


@pytest.fixture
def indexed(db_session, fake_encoder, image_root):
    report = visual_search.build_index(db_session, fake_encoder)
    return report, image_root[1]
