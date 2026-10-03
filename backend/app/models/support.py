"""Customer support conversations between a customer and the store.

Plain-text messages stored in PostgreSQL; clients poll for new ones. A
conversation may be linked to one of the customer's orders or returns.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.order import _enum


class SupportSubject(enum.StrEnum):
    sizing = "sizing"
    delivery = "delivery"
    order_issue = "order_issue"
    return_question = "return_question"
    other = "other"


class ConversationStatus(enum.StrEnum):
    open = "open"
    closed = "closed"


class SenderRole(enum.StrEnum):
    customer = "customer"
    store = "store"


class SupportConversation(Base):
    __tablename__ = "support_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Customer-facing reference, e.g. KS-2026-4HF7QZ.
    conversation_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    return_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("return_requests.id", ondelete="SET NULL"), index=True
    )
    subject: Mapped[SupportSubject] = mapped_column(_enum(SupportSubject, "support_subject"))
    status: Mapped[ConversationStatus] = mapped_column(
        _enum(ConversationStatus, "conversation_status", 10),
        default=ConversationStatus.open,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # For "last activity" sorting without scanning messages.
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["SupportMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="SupportMessage.id"
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"
    __table_args__ = (
        # Polling reads "messages of this conversation after id N".
        Index("ix_support_messages_conversation_id_id", "conversation_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("support_conversations.id", ondelete="CASCADE")
    )
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # Decided by the endpoint used (customer or admin), never by the client.
    sender_role: Mapped[SenderRole] = mapped_column(_enum(SenderRole, "sender_role", 10))
    # Plain text, shown escaped. Never interpreted as HTML.
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # When the other side first loaded it (customer reads store messages and vice versa).
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[SupportConversation] = relationship(back_populates="messages")
