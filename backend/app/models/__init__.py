"""SQLAlchemy models.

Import every model module here so `Base.metadata` (and therefore Alembic
autogenerate) knows about all tables.
"""

from app.models.catalog import (
    Category,
    Gender,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)

__all__ = [
    "Category",
    "Gender",
    "Inventory",
    "Product",
    "ProductImage",
    "ProductVariant",
]
