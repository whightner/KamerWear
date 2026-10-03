"""Check visual search quality with the real model (after preparing and indexing).

    python -m app.ai.evaluate_visual_search

For a few catalog products of different types, searches with the original
photo and with transformed versions (crop, small padded "screenshot", heavy
JPEG recompression, coloured background). Prints the predicted type, whether
the guard was applied, the top results and timings, and where the source
product ranked. Uses no fake data: it fails if the model isn't available.
"""

import io
import sys
import time

from PIL import Image, ImageOps
from sqlalchemy import select

from app.ai.encoder import EncoderUnavailable, get_encoder
from app.ai.images import catalog_image_path, open_catalog_image
from app.db.session import SessionLocal
from app.models import Product
from app.services.errors import ServiceError
from app.services.visual_search import search_by_image

SAMPLES = [
    "urban-runner-02",
    "classic-hoodie",
    "canvas-messenger-bag",
    "everyday-cargo",
    "core-heavy-tee",
]


def _jpeg(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")


TRANSFORMS = {
    "original": lambda im: im,
    "centre crop 70%": lambda im: ImageOps.crop(
        im, border=(int(im.width * 0.15), int(im.height * 0.15))
    ),
    "screenshot (small, padded)": lambda im: ImageOps.pad(
        im.resize((im.width // 3, im.height // 3)), (600, 400), color=(245, 245, 245)
    ),
    "JPEG quality 25": lambda im: _jpeg(im, 25),
    "coloured background": lambda im: ImageOps.expand(im, border=im.width // 4, fill=(40, 90, 160)),
}


def main() -> int:
    try:
        encoder = get_encoder()
    except EncoderUnavailable as exc:
        print(f"Model unavailable, nothing evaluated: {exc}", file=sys.stderr)
        return 1
    print(f"Model {encoder.model_name}\n")
    times = []
    with SessionLocal() as db:
        for slug in SAMPLES:
            product = db.scalar(select(Product).where(Product.slug == slug))
            if product is None or not product.images:
                print(f"- {slug}: not in the catalog, skipped")
                continue
            source = open_catalog_image(catalog_image_path(product.images[0].image_path))
            print(f"{product.name} ({product.product_type})")
            for name, transform in TRANSFORMS.items():
                query = transform(source)
                started = time.monotonic()
                try:
                    result = search_by_image(db, encoder, query, limit=5)
                except ServiceError as exc:
                    print(f"  {name}: {exc.code}")
                    continue
                elapsed = (time.monotonic() - started) * 1000
                times.append(elapsed)
                slugs = [m.product.slug for m in result.matches]
                rank = slugs.index(slug) + 1 if slug in slugs else None
                top = ", ".join(
                    f"{m.product.product_type}:{m.product.slug}({m.score:.2f})"
                    for m in result.matches[:3]
                )
                guard = result.prediction.top_group if result.prediction else "-"
                print(
                    f"  {name:<28} type={guard:<10} guard={'yes' if result.guard_applied else 'no ':<3} "
                    f"source rank={rank or '>5'}  {elapsed:.0f} ms  top: {top}"
                )
            print()
    if times:
        print(
            f"Average search time (encode + type guard + ranking): {sum(times) / len(times):.0f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
