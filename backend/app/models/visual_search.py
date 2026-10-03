"""Visual search index: one image embedding per product image and model.

Embeddings are stored as raw little-endian float32 bytes (512 floats = 2 KB
for ViT-B-32). The catalog is small (about 70 images), so the search loads
them and computes cosine similarity with NumPy; pgvector isn't needed.
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalog import ProductImage


class ProductImageEmbedding(Base):
    __tablename__ = "product_image_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "product_image_id", "model_name", name="uq_product_image_embeddings_image_model"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_image_id: Mapped[int] = mapped_column(
        ForeignKey("product_images.id", ondelete="CASCADE"), index=True
    )
    # e.g. "ViT-B-32/laion2b_s34b_b79k"; embeddings of different models never mix.
    model_name: Mapped[str] = mapped_column(String(120))
    dimensions: Mapped[int] = mapped_column(Integer)
    # L2-normalised float32 vector.
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    # What was encoded: if the image path or file content changes, the row is stale.
    source_path: Mapped[str] = mapped_column(String(255))
    source_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    image: Mapped[ProductImage] = relationship()


class VisualSearchIndexRun(Base):
    """One run of the index builder (CLI or admin button), for the status page."""

    __tablename__ = "visual_search_index_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(120))
    trigger: Mapped[str] = mapped_column(String(20))  # "cli" or "admin"
    status: Mapped[str] = mapped_column(String(20))  # "running", "succeeded", "failed"
    indexed: Mapped[int] = mapped_column(Integer, default=0)
    unchanged: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    removed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
