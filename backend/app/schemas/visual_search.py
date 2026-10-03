"""Visual search responses. Embeddings are never returned."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.catalog import ProductListItem


class VisualSearchItem(BaseModel):
    product: ProductListItem
    # Cosine similarity of the best-matching catalog image (-1..1). A ranking
    # value for debugging, not a probability or accuracy.
    similarity_score: float
    matched_image: str
    # True/False when the type guard was applied; null otherwise.
    matches_predicted_type: bool | None


class VisualSearchQuery(BaseModel):
    predicted_type: str | None = Field(description="Type group used by the guard, e.g. footwear.")
    predicted_type_label: str | None
    type_guard_applied: bool
    # The best match is weak: show "closest products currently available".
    weak_matches: bool
    model: str
    search_ms: int


class VisualSearchResponse(BaseModel):
    query: VisualSearchQuery
    items: list[VisualSearchItem]


class VisualSimilarResponse(BaseModel):
    type_guard_applied: bool
    weak_matches: bool
    model: str
    items: list[VisualSearchItem]


class IndexRunSummary(BaseModel):
    trigger: str
    status: str
    indexed: int
    unchanged: int
    failed: int
    removed: int
    message: str | None
    started_at: datetime
    finished_at: datetime | None


class VisualSearchStatus(BaseModel):
    model: str
    # "loaded", "not_loaded" (loads on first use) or "failed".
    encoder_state: str
    ready: bool
    active_images: int
    indexed_images: int
    products_represented: int
    active_products: int
    stale_images: list[str]
    unindexed_images: list[str]
    missing_files: list[str]
    last_run: IndexRunSummary | None


class RebuildResult(BaseModel):
    model: str
    indexed: int
    unchanged: int
    failed: int
    removed: int
    seconds: float
    problems: list[str]
