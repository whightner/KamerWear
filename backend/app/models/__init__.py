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
from app.models.user import AuthSession, Role, User, UserProfile

__all__ = [
    "AuthSession",
    "Category",
    "Gender",
    "Inventory",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Role",
    "User",
    "UserProfile",
]
