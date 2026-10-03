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
from app.models.fit import FitEstimate, FitPreference, FitProfile
from app.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    PaymentStatus,
    PaymentStatusHistory,
)
from app.models.returns import (
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnStatus,
    ReturnStatusHistory,
)
from app.models.support import (
    ConversationStatus,
    SenderRole,
    SupportConversation,
    SupportMessage,
    SupportSubject,
)
from app.models.visual_search import ProductImageEmbedding, VisualSearchIndexRun
from app.models.user import AuthSession, Role, User, UserProfile

__all__ = [
    "Address",
    "AuthSession",
    "Cart",
    "CartItem",
    "Category",
    "ConversationStatus",
    "Gender",
    "FitEstimate",
    "FitPreference",
    "FitProfile",
    "Inventory",
    "Order",
    "OrderItem",
    "OrderStatus",
    "OrderStatusHistory",
    "PaymentMethod",
    "PaymentStatus",
    "PaymentStatusHistory",
    "Product",
    "ProductImage",
    "ProductImageEmbedding",
    "ProductVariant",
    "ReturnItem",
    "ReturnReason",
    "ReturnRequest",
    "ReturnStatus",
    "ReturnStatusHistory",
    "Role",
    "SenderRole",
    "SupportConversation",
    "SupportMessage",
    "SupportSubject",
    "User",
    "UserProfile",
    "VisualSearchIndexRun",
]
