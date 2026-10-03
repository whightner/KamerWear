"""Support conversations and messages. Message bodies are plain text."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import (
    ConversationStatus,
    OrderStatus,
    ReturnStatus,
    SenderRole,
    SupportSubject,
)
from app.schemas.admin_store import CustomerRef

# Hard cap on the request size; the service enforces the real limit
# (SUPPORT_MESSAGE_MAX_LENGTH) with a clear `message_too_long` error.
Body = Annotated[str, Field(max_length=10_000)]
Reference = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: SupportSubject
    message: Body
    order_number: Reference | None = None
    return_number: Reference | None = None


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: Body


class MessageResponse(BaseModel):
    id: int
    sender_role: SenderRole
    # "KamerWear support" for store messages, the customer's first name otherwise.
    sender_name: str
    body: str
    created_at: datetime
    read_at: datetime | None


class ConversationSummary(BaseModel):
    conversation_number: str
    subject: SupportSubject
    subject_label: str
    status: ConversationStatus
    order_number: str | None
    return_number: str | None
    last_message_preview: str | None
    last_message_role: SenderRole | None
    last_message_at: datetime
    # Messages from the other side not read yet.
    unread_count: int
    created_at: datetime


class ConversationDetail(ConversationSummary):
    closed_at: datetime | None
    messages: list[MessageResponse]
    last_message_id: int


class ConversationList(BaseModel):
    items: list[ConversationSummary]
    total: int
    limit: int
    offset: int


class NewMessages(BaseModel):
    """Polling answer: only messages after `after_id`, plus the current status."""

    status: ConversationStatus
    messages: list[MessageResponse]
    last_message_id: int


class UnreadCount(BaseModel):
    unread: int


# --- Admin -------------------------------------------------------------------------


class AdminConversationSummary(ConversationSummary):
    customer: CustomerRef


class AdminConversationList(BaseModel):
    items: list[AdminConversationSummary]
    total: int
    limit: int
    offset: int


class LinkedOrder(BaseModel):
    order_number: str
    status: OrderStatus
    total: int


class LinkedReturn(BaseModel):
    return_number: str
    status: ReturnStatus
    return_value: int


class AdminConversationDetail(AdminConversationSummary):
    closed_at: datetime | None
    messages: list[MessageResponse]
    last_message_id: int
    order: LinkedOrder | None
    return_request: LinkedReturn | None


class AttentionCounts(BaseModel):
    """Admin navigation badges."""

    returns_to_process: int
    conversations_unread: int
