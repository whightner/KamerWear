"""SQLAlchemy models.

Import every model module here so `Base.metadata` (and therefore Alembic
autogenerate) knows about all tables.
"""

from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.models.catalog import (
    Category,
    Gender,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)
from app.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    PaymentStatus,
)
from app.models.user import AuthSession, Role, User, UserProfile

__all__ = [
    "Address",
    "AuthSession",
    "Cart",
    "CartItem",
    "Category",
    "Gender",
    "Inventory",
    "Order",
    "OrderItem",
    "OrderStatus",
    "OrderStatusHistory",
    "PaymentMethod",
    "PaymentStatus",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Role",
    "User",
    "UserProfile",
]
