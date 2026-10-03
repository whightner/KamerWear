"""Seed the demo catalog.

    python -m app.db.seed

Idempotent: categories, products and variants are matched by slug or SKU and
updated in place, images are replaced, so running it twice never duplicates
data. Inventory is reset to the demo stock levels on every run.

The data comes from seed_data/catalog.json, an export of the frontend mock
catalog (frontend/src/data/products.ts) so the API serves the same products.
"""

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal
from app.models import (
    Category,
    Gender,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)

CATALOG_FILE = Path(__file__).parent / "seed_data" / "catalog.json"

CATEGORIES = {
    "shoes": ("Shoes", "Sneakers and everyday footwear."),
    "clothing": ("Clothing", "Tops, hoodies, jackets and trousers."),
    "accessories": ("Accessories", "Bags and other accessories."),
}

# A few units held for unpaid orders, to exercise available = on_hand - reserved.
DEMO_RESERVATIONS = {"CJ-BLACK-S": 2}


# Products whose initials would collide with another product's.
SKU_PREFIX_OVERRIDES = {"striped-zip-hoodie": "STZH", "sunset-zip-hoodie": "SNZH"}


def sku_prefix(slug: str) -> str:
    """urban-runner-02 -> UR02, classic-hoodie -> CH."""
    if slug in SKU_PREFIX_OVERRIDES:
        return SKU_PREFIX_OVERRIDES[slug]
    return "".join(part if part.isdigit() else part[0] for part in slug.split("-")).upper()


def sku_for(slug: str, color_slug: str, size: str | None) -> str:
    color = re.sub(r"[^A-Z0-9]", "", color_slug.upper())
    return f"{sku_prefix(slug)}-{color}-{size or 'OS'}"


def distribute(stock: int, variant_count: int) -> list[int]:
    """Spread a product's demo stock evenly over its sellable variants."""
    if variant_count == 0:
        return []
    base, extra = divmod(stock, variant_count)
    return [base + (1 if i < extra else 0) for i in range(variant_count)]


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def seed_catalog(session: Session) -> dict[str, int]:
    categories = _seed_categories(session)
    for data in load_catalog():
        _seed_product(session, data, categories[data["category"]])
    session.commit()
    return {
        "categories": len(session.scalars(select(Category)).all()),
        "products": len(session.scalars(select(Product)).all()),
        "images": len(session.scalars(select(ProductImage)).all()),
        "variants": len(session.scalars(select(ProductVariant)).all()),
    }


def _seed_categories(session: Session) -> dict[str, Category]:
    existing = {c.slug: c for c in session.scalars(select(Category))}
    for slug, (name, description) in CATEGORIES.items():
        category = existing.get(slug) or Category(slug=slug)
        category.name, category.description, category.is_active = name, description, True
        session.add(category)
        existing[slug] = category
    session.flush()
    return existing


def _seed_product(session: Session, data: dict[str, Any], category: Category) -> None:
    product = session.scalar(
        select(Product)
        .where(Product.slug == data["slug"])
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.inventory),
        )
    )
    if product is None:
        product = Product(slug=data["slug"])
        session.add(product)

    product.category = category
    product.name = data["name"]
    product.description = data["description"]
    product.gender = Gender(data["gender"])
    product.product_type = data["type"]
    product.base_price = data["price"]
    product.compare_at_price = data.get("oldPrice")
    product.rating_average = Decimal(str(data["rating"]))
    product.review_count = data["reviewCount"]
    product.smart_fit = data.get("smartFit", False)
    product.smart_fit_demo_size = data.get("smartFitDemoSize")
    product.search_keywords = " ".join(data.get("tags", []))
    product.is_new = data.get("isNew", False)
    product.featured = data.get("featured", False)
    product.is_active = True

    # Images: replaced wholesale, ordered by colour then view.
    product.images.clear()
    session.flush()
    position = 0
    for color in data["colors"]:
        for image in color["images"]:
            product.images.append(
                ProductImage(
                    image_path=image["src"],
                    alt_text=image["alt"],
                    position=position,
                    color_name=color["name"],
                )
            )
            position += 1

    # Variants: one per colour x size (a single "one size" variant for bags).
    variants_by_sku = {v.sku: v for v in product.variants}
    sold_out = set(data.get("soldOutSizes", []))
    sellable: list[ProductVariant] = []
    seeded_skus: set[str] = set()
    for color in data["colors"]:
        for size in data["sizes"] or [None]:
            sku = sku_for(data["slug"], color["slug"], size)
            seeded_skus.add(sku)
            variant = variants_by_sku.get(sku)
            if variant is None:
                variant = ProductVariant(sku=sku)
                product.variants.append(variant)
            variant.size = size
            variant.color_name = color["name"]
            variant.color_hex = color["swatch"]
            variant.price_override = None
            variant.is_active = True
            if variant.inventory is None:
                variant.inventory = Inventory()
            variant.inventory.on_hand = 0
            variant.inventory.reserved = 0
            if size not in sold_out:
                sellable.append(variant)

    # Variants no longer in the seed data are removed (with their inventory).
    for variant in [v for v in product.variants if v.sku not in seeded_skus]:
        product.variants.remove(variant)

    # Inventory: the product's demo stock is spread over sellable variants, so
    # totals, low-stock and sold-out states match the frontend demo.
    for variant, units in zip(sellable, distribute(data["stock"], len(sellable)), strict=True):
        reserved = DEMO_RESERVATIONS.get(variant.sku, 0)
        variant.inventory.on_hand = units + reserved
        variant.inventory.reserved = reserved
    session.flush()


def main() -> None:
    with SessionLocal() as session:
        counts = seed_catalog(session)
    print("Seeded catalog:", ", ".join(f"{n} {k}" for k, n in counts.items()))


if __name__ == "__main__":
    main()
