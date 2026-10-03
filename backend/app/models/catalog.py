"""Catalog tables: categories, products, images, variants and inventory.

Money columns hold whole XAF (FCFA) as integers. Never use floats for money.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Gender(enum.StrEnum):
    men = "men"
    women = "women"
    unisex = "unisex"


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def _updated_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


def discount_percent(price: int, compare_at_price: int | None) -> int | None:
    """Whole-number discount, rounded half up like the frontend (28500 vs 39900 -> 29)."""
    if not compare_at_price or compare_at_price <= price:
        return None
    return (200 * (compare_at_price - price) + compare_at_price) // (2 * compare_at_price)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="base_price_non_negative"),
        CheckConstraint(
            "compare_at_price IS NULL OR compare_at_price >= 0",
            name="compare_at_price_non_negative",
        ),
        CheckConstraint("rating_average BETWEEN 0 AND 5", name="rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    gender: Mapped[Gender] = mapped_column(
        Enum(
            Gender,
            native_enum=False,
            length=10,
            create_constraint=True,
            name="gender",
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
    )
    product_type: Mapped[str] = mapped_column(String(50), index=True)
    base_price: Mapped[int] = mapped_column(Integer)
    compare_at_price: Mapped[int | None] = mapped_column(Integer)
    # Seeded demo metadata until a real review system exists.
    rating_average: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("0"))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    smart_fit: Mapped[bool] = mapped_column(Boolean, default=False)
    # Size shown by the Smart Fit demo state; no real Fit Profiles exist yet.
    smart_fit_demo_size: Mapped[str | None] = mapped_column(String(10))
    # Extra space-separated search words, e.g. "streetwear running".
    search_keywords: Mapped[str] = mapped_column(String(255), default="")
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    category: Mapped[Category] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        # Position first; id breaks ties so the gallery order is always the same.
        order_by="(ProductImage.position, ProductImage.id)",
        cascade="all, delete-orphan",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product",
        order_by="ProductVariant.id",
        cascade="all, delete-orphan",
    )

    # Derived values used by the API schemas. They expect images, variants and
    # inventory to be loaded up front (see services/catalog.py) to avoid N+1 queries.

    @property
    def price(self) -> int:
        return self.base_price

    @property
    def discount_percent(self) -> int | None:
        return discount_percent(self.base_price, self.compare_at_price)

    @property
    def active_variants(self) -> list["ProductVariant"]:
        return [v for v in self.variants if v.is_active]

    @property
    def primary_image(self) -> "ProductImage | None":
        return self.images[0] if self.images else None

    @property
    def sizes(self) -> list[str]:
        """Distinct sizes in catalog order; empty for one-size products."""
        return list(dict.fromkeys(v.size for v in self.active_variants if v.size))

    @property
    def colors(self) -> list[dict[str, str]]:
        seen: dict[str, str] = {}
        for v in self.active_variants:
            seen.setdefault(v.color_name, v.color_hex)
        return [{"name": name, "hex": hex_} for name, hex_ in seen.items()]

    @property
    def available_quantity(self) -> int:
        return sum(v.available_quantity for v in self.active_variants)

    @property
    def in_stock(self) -> bool:
        return self.available_quantity > 0


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "image_path", name="uq_product_images_product_id_image_path"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    # Path of a static frontend asset, e.g. /images/products/<slug>/black-1.webp.
    image_path: Mapped[str] = mapped_column(String(255))
    alt_text: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Lets galleries switch with the selected colour; null means "any colour".
    color_name: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = _created_at()

    product: Mapped[Product] = relationship(back_populates="images")


class ProductVariant(Base):
    """A sellable colour/size combination of a product."""

    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint(
            "price_override IS NULL OR price_override >= 0",
            name="price_override_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    # Null for one-size products such as bags.
    size: Mapped[str | None] = mapped_column(String(10))
    color_name: Mapped[str] = mapped_column(String(50))
    color_hex: Mapped[str] = mapped_column(String(7))
    price_override: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    product: Mapped[Product] = relationship(back_populates="variants")
    inventory: Mapped["Inventory | None"] = relationship(
        back_populates="variant", cascade="all, delete-orphan", uselist=False
    )

    @property
    def price(self) -> int:
        """Effective price: the override when set, otherwise the product base price."""
        return self.price_override if self.price_override is not None else self.product.base_price

    @property
    def available_quantity(self) -> int:
        return self.inventory.available if self.inventory else 0

    @property
    def in_stock(self) -> bool:
        return self.available_quantity > 0


class Inventory(Base):
    """Stock for one variant. No movement history or warehouses in the MVP."""

    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("on_hand >= 0", name="on_hand_non_negative"),
        CheckConstraint("reserved >= 0", name="reserved_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), unique=True
    )
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = _updated_at()

    variant: Mapped[ProductVariant] = relationship(back_populates="inventory")

    @property
    def available(self) -> int:
        """on_hand - reserved, never reported below zero."""
        return max(0, self.on_hand - self.reserved)
