"""Visual search: index catalog images, search by photo, find visually similar products.

    photo ──► pretrained encoder ──► embedding ─┐
                                                ├─► cosine similarity ─► best image per product
    catalog images ──► (same encoder, indexed) ─┘        + type guard ─► ranked products

Scores come only from image embeddings. Names, keywords and file names play
no part. The optional type guard (type_guard.py) only reorders: products of
the confidently predicted type come first.
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.ai.encoder import ImageEncoder, active_model_name
from app.ai.images import catalog_image_path, open_catalog_image
from app.ai.type_guard import TypeGuard, TypePrediction, product_group
from app.models import (
    Category,
    Product,
    ProductImage,
    ProductImageEmbedding,
    ProductVariant,
    VisualSearchIndexRun,
)
from app.services.errors import ServiceError

# pg_try_advisory_lock key: only one index build at a time, CLI or admin.
INDEX_LOCK_KEY = 0x4B57_5649  # "KWVI"
BATCH_SIZE = 16
# Below this best score, results are labelled "closest available" (heuristic
# for ViT-B-32 image-image cosine similarity; not a probability).
WEAK_MATCH_SCORE = 0.55


def unavailable() -> ServiceError:
    return ServiceError(
        503,
        "visual_search_unavailable",
        "Visual search is unavailable right now. Please try again later or browse the shop.",
    )


def not_ready() -> ServiceError:
    return ServiceError(
        503,
        "visual_search_not_ready",
        "Visual search isn't ready yet: the catalog images haven't been indexed.",
    )


# --- Indexing --------------------------------------------------------------------


def _active_images(db: Session) -> list[ProductImage]:
    return list(
        db.scalars(
            select(ProductImage)
            .join(Product, Product.id == ProductImage.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(Product.is_active.is_(True), Category.is_active.is_(True))
            .order_by(ProductImage.id)
        )
    )


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class IndexReport:
    model_name: str
    indexed: int = 0
    unchanged: int = 0
    failed: int = 0
    removed: int = 0
    problems: list[str] = field(default_factory=list)
    seconds: float = 0.0


class IndexBusy(Exception):
    pass


def build_index(
    db: Session, encoder: ImageEncoder, *, trigger: str = "cli", force: bool = False
) -> IndexReport:
    """Encodes new or changed images of active products; removes obsolete rows.

    Safe to run repeatedly: unchanged images (same path, same file content,
    same model) are skipped, and rows are updated in place, never duplicated.
    """
    if not db.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": INDEX_LOCK_KEY}):
        raise IndexBusy("Another index build is already running.")
    started = time.monotonic()
    report = IndexReport(model_name=encoder.model_name)
    run = VisualSearchIndexRun(model_name=encoder.model_name, trigger=trigger, status="running")
    db.add(run)
    db.commit()
    try:
        images = _active_images(db)
        existing = {
            row.product_image_id: row
            for row in db.scalars(
                select(ProductImageEmbedding).where(
                    ProductImageEmbedding.model_name == encoder.model_name
                )
            )
        }
        pending: list[tuple[ProductImage, str]] = []  # (image, sha256)
        loaded = []
        for image in images:
            try:
                path = catalog_image_path(image.image_path)
                digest = _sha256(path)
            except (ValueError, OSError) as exc:
                report.failed += 1
                report.problems.append(f"{image.image_path}: {type(exc).__name__}")
                continue
            row = existing.get(image.id)
            if (
                not force
                and row is not None
                and row.source_path == image.image_path
                and row.source_sha256 == digest
            ):
                report.unchanged += 1
                continue
            pending.append((image, digest))
            loaded.append(path)

        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            pictures = []
            usable = []
            for (image, digest), path in zip(
                batch, loaded[start : start + BATCH_SIZE], strict=True
            ):
                try:
                    pictures.append(open_catalog_image(path))
                    usable.append((image, digest))
                except OSError as exc:
                    report.failed += 1
                    report.problems.append(f"{image.image_path}: {type(exc).__name__}")
            if not pictures:
                continue
            vectors = encoder.encode_images(pictures)
            for (image, digest), vector in zip(usable, vectors, strict=True):
                row = existing.get(image.id)
                if row is None:
                    row = ProductImageEmbedding(
                        product_image_id=image.id, model_name=encoder.model_name
                    )
                    db.add(row)
                    existing[image.id] = row
                row.dimensions = int(vector.shape[0])
                row.embedding = vector.astype("<f4").tobytes()
                row.source_path = image.image_path
                row.source_sha256 = digest
                report.indexed += 1
            db.flush()

        # Obsolete rows: images now inactive/deleted, or from another model.
        active_ids = [image.id for image in images]
        result = db.execute(
            delete(ProductImageEmbedding).where(
                (ProductImageEmbedding.model_name != encoder.model_name)
                | ProductImageEmbedding.product_image_id.not_in(active_ids or [-1])
            )
        )
        report.removed = result.rowcount or 0
        report.seconds = round(time.monotonic() - started, 2)
        run.status = "succeeded"
        run.indexed, run.unchanged = report.indexed, report.unchanged
        run.failed, run.removed = report.failed, report.removed
        run.message = "; ".join(report.problems)[:500] or None
        run.finished_at = datetime.now(UTC)
        db.commit()
        return report
    except Exception:
        db.rollback()
        run = db.get(VisualSearchIndexRun, run.id)
        if run is not None:
            run.status = "failed"
            run.message = "The index build stopped with an error (see server logs)."
            run.finished_at = datetime.now(UTC)
            db.commit()
        raise
    finally:
        db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": INDEX_LOCK_KEY})
        db.commit()


# --- Status ----------------------------------------------------------------------


@dataclass
class IndexStatus:
    model_name: str
    encoder_state: str
    active_images: int
    indexed_images: int
    stale_images: list[str]
    unindexed_images: list[str]
    missing_files: list[str]
    products_represented: int
    active_products: int
    last_run: VisualSearchIndexRun | None
    ready: bool


def index_status(db: Session, encoder_state: str) -> IndexStatus:
    model_name = active_model_name()
    images = _active_images(db)
    rows = {
        row.product_image_id: row
        for row in db.scalars(
            select(ProductImageEmbedding).where(ProductImageEmbedding.model_name == model_name)
        )
    }
    stale, unindexed, missing = [], [], []
    represented: set[int] = set()
    for image in images:
        try:
            digest = _sha256(catalog_image_path(image.image_path))
        except (ValueError, OSError):
            missing.append(image.image_path)
            continue
        row = rows.get(image.id)
        if row is None:
            unindexed.append(image.image_path)
        elif row.source_path != image.image_path or row.source_sha256 != digest:
            stale.append(image.image_path)
            represented.add(image.product_id)
        else:
            represented.add(image.product_id)
    active_products = (
        db.scalar(
            select(func.count(Product.id))
            .join(Category, Category.id == Product.category_id)
            .where(Product.is_active.is_(True), Category.is_active.is_(True))
        )
        or 0
    )
    last_run = db.scalar(
        select(VisualSearchIndexRun).order_by(VisualSearchIndexRun.id.desc()).limit(1)
    )
    indexed = len(images) - len(stale) - len(unindexed) - len(missing)
    return IndexStatus(
        model_name=model_name,
        encoder_state=encoder_state,
        active_images=len(images),
        indexed_images=indexed,
        stale_images=stale,
        unindexed_images=unindexed,
        missing_files=missing,
        products_represented=len(represented),
        active_products=active_products,
        last_run=last_run,
        ready=indexed > 0,
    )


# --- Searching -------------------------------------------------------------------


@dataclass
class IndexedImage:
    product_id: int
    image_path: str
    group: str | None


def _load_index(db: Session, model_name: str) -> tuple[list[IndexedImage], np.ndarray]:
    """Embeddings of active products' images (inactive products are never returned)."""
    rows = db.execute(
        select(
            ProductImageEmbedding.embedding,
            ProductImage.product_id,
            ProductImage.image_path,
            Product.product_type,
            Category.slug,
        )
        .join(ProductImage, ProductImage.id == ProductImageEmbedding.product_image_id)
        .join(Product, Product.id == ProductImage.product_id)
        .join(Category, Category.id == Product.category_id)
        .where(
            ProductImageEmbedding.model_name == model_name,
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
        .order_by(ProductImage.product_id, ProductImage.position, ProductImage.id)
    ).all()
    entries = [
        IndexedImage(product_id=pid, image_path=path, group=product_group(ptype, cslug))
        for _, pid, path, ptype, cslug in rows
    ]
    matrix = (
        np.vstack([np.frombuffer(row[0], dtype="<f4") for row in rows])
        if rows
        else np.zeros((0, 0), dtype=np.float32)
    )
    return entries, matrix


def _any_index(db: Session, model_name: str) -> bool:
    return (
        db.scalar(
            select(ProductImageEmbedding.id)
            .where(ProductImageEmbedding.model_name == model_name)
            .limit(1)
        )
        is not None
    )


@dataclass
class Match:
    product: Product
    score: float
    matched_image: str
    in_predicted_type: bool | None


@dataclass
class SearchResult:
    matches: list[Match]
    prediction: TypePrediction | None
    guard_applied: bool
    weak: bool
    model_name: str
    milliseconds: int


def _rank(
    entries: list[IndexedImage],
    scores: np.ndarray,
    *,
    limit: int,
    preferred_group: str | None,
    exclude_product: int | None = None,
) -> list[tuple[int, float, str, bool | None]]:
    """Best image per product (max cosine), then guard order, then score."""
    best: dict[int, tuple[float, str, str | None]] = {}
    for entry, score in zip(entries, scores, strict=True):
        if entry.product_id == exclude_product:
            continue
        current = best.get(entry.product_id)
        if current is None or score > current[0]:
            best[entry.product_id] = (float(score), entry.image_path, entry.group)
    ranked = [
        (pid, score, path, (group == preferred_group) if preferred_group else None)
        for pid, (score, path, group) in best.items()
    ]
    ranked.sort(key=lambda r: (not r[3] if preferred_group else False, -r[1], r[0]))
    return ranked[:limit]


def _load_products(db: Session, ids: list[int]) -> dict[int, Product]:
    products = db.scalars(
        select(Product)
        .where(Product.id.in_(ids))
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.inventory),
        )
    ).unique()
    return {product.id: product for product in products}


_guards: dict[str, TypeGuard] = {}


def _type_guard(encoder: ImageEncoder) -> TypeGuard:
    guard = _guards.get(encoder.model_name)
    if guard is None or guard.model_name != encoder.model_name:
        guard = TypeGuard(encoder)
        _guards.clear()
        _guards[encoder.model_name] = guard
    return guard


def reset_type_guard_cache() -> None:
    _guards.clear()


def search_by_image(db: Session, encoder: ImageEncoder, image, *, limit: int) -> SearchResult:
    started = time.monotonic()
    entries, matrix = _load_index(db, encoder.model_name)
    if not entries:
        if _any_index(db, encoder.model_name):
            raise ServiceError(
                404,
                "no_searchable_products",
                "No products are available for visual search right now.",
            )
        raise not_ready()
    query = encoder.encode_images([image])[0]
    prediction = _type_guard(encoder).predict(query)
    preferred = prediction.group
    # Only apply the guard if the catalog actually has products of that type.
    guard_applied = preferred is not None and any(e.group == preferred for e in entries)
    ranked = _rank(
        entries, matrix @ query, limit=limit, preferred_group=preferred if guard_applied else None
    )
    products = _load_products(db, [pid for pid, *_ in ranked])
    matches = [
        Match(products[pid], round(score, 4), path, in_type)
        for pid, score, path, in_type in ranked
        if pid in products
    ]
    weak = not matches or matches[0].score < WEAK_MATCH_SCORE
    return SearchResult(
        matches=matches,
        prediction=prediction,
        guard_applied=guard_applied,
        weak=weak,
        model_name=encoder.model_name,
        milliseconds=int((time.monotonic() - started) * 1000),
    )


def similar_to_product(
    db: Session, encoder_model: str, product: Product, *, limit: int
) -> SearchResult:
    """Products that look like `product`, from its own indexed image embeddings.

    Query = the normalised mean of the product's image embeddings. The product's
    catalog type is used as the guard (no zero-shot needed); the product itself
    is excluded. Needs no model inference, only the stored vectors.
    """
    started = time.monotonic()
    entries, matrix = _load_index(db, encoder_model)
    own = [i for i, e in enumerate(entries) if e.product_id == product.id]
    if not own:
        if not _any_index(db, encoder_model):
            raise not_ready()
        raise ServiceError(
            409,
            "product_not_indexed",
            "This product's images aren't in the visual search index yet.",
        )
    query = matrix[own].mean(axis=0)
    query /= max(float(np.linalg.norm(query)), 1e-12)
    group = product_group(product.product_type, product.category.slug)
    guard_applied = group is not None and any(
        e.group == group and e.product_id != product.id for e in entries
    )
    ranked = _rank(
        entries,
        matrix @ query,
        limit=limit,
        preferred_group=group if guard_applied else None,
        exclude_product=product.id,
    )
    products = _load_products(db, [pid for pid, *_ in ranked])
    matches = [
        Match(products[pid], round(score, 4), path, in_type)
        for pid, score, path, in_type in ranked
        if pid in products
    ]
    return SearchResult(
        matches=matches,
        prediction=None,
        guard_applied=guard_applied,
        weak=not matches or matches[0].score < WEAK_MATCH_SCORE,
        model_name=encoder_model,
        milliseconds=int((time.monotonic() - started) * 1000),
    )
