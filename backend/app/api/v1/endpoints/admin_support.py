"""Admin: store-wide support conversations and replies (ADMIN only).

Replies sent here are always `store` messages.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, DbSession, require_admin
from app.api.v1.endpoints.support import entry_for, message_responses, summary_fields
from app.models import (
    ConversationStatus,
    Order,
    ReturnRequest,
    SenderRole,
    SupportConversation,
    User,
)
from app.schemas.catalog import ErrorResponse
from app.schemas.support import (
    AdminConversationDetail,
    AdminConversationList,
    AdminConversationSummary,
    AttentionCounts,
    LinkedOrder,
    LinkedReturn,
    MessageCreate,
    MessageResponse,
    NewMessages,
)
from app.services import admin_store
from app.services import returns as return_service
from app.services import support as service

router = APIRouter(
    prefix="/admin",
    tags=["admin: support"],
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "authentication_required"},
        403: {"model": ErrorResponse, "description": "admin_required"},
    },
)
NOT_FOUND = {404: {"model": ErrorResponse, "description": "conversation_not_found"}}


def _detail(db, conversation: SupportConversation) -> AdminConversationDetail:
    service.mark_read(db, conversation, SenderRole.store)
    db.commit()
    messages = service.messages_after(db, conversation)
    order = db.get(Order, conversation.order_id) if conversation.order_id else None
    request = (
        db.get(ReturnRequest, conversation.return_request_id)
        if conversation.return_request_id
        else None
    )
    return AdminConversationDetail(
        **summary_fields(entry_for(db, conversation, SenderRole.store)),
        customer=admin_store._customer(db.get(User, conversation.user_id)),
        closed_at=conversation.closed_at,
        messages=message_responses(db, messages),
        last_message_id=messages[-1].id if messages else 0,
        order=LinkedOrder(order_number=order.order_number, status=order.status, total=order.total)
        if order
        else None,
        return_request=LinkedReturn(
            return_number=request.return_number,
            status=request.status,
            return_value=request.return_value,
        )
        if request
        else None,
    )


@router.get("/attention", summary="Navigation badges: returns to process, unread conversations")
def attention(db: DbSession) -> AttentionCounts:
    return AttentionCounts(
        returns_to_process=return_service.requested_count(db),
        conversations_unread=service.conversations_needing_reply(db),
    )


@router.get("/support/conversations", summary="All support conversations, latest activity first")
def list_conversations(
    db: DbSession,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Conversation, order or return number, email, name"),
    ] = None,
    status: ConversationStatus | None = None,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminConversationList:
    rows, total = service.list_all(
        db, q=q, status=status, unread_only=unread_only, limit=limit, offset=offset
    )
    return AdminConversationList(
        items=[
            AdminConversationSummary(**summary_fields(e), customer=admin_store._customer(u))
            for e, u in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/support/conversations/{number}",
    summary="Any conversation (marks customer messages as read)",
    responses=NOT_FOUND,
)
def read_conversation(number: str, db: DbSession) -> AdminConversationDetail:
    return _detail(db, service.get_any(db, number))


@router.get(
    "/support/conversations/{number}/messages",
    summary="Polling: messages after a given id",
    responses=NOT_FOUND,
)
def new_messages(
    number: str, db: DbSession, after_id: Annotated[int, Query(ge=0)] = 0
) -> NewMessages:
    conversation = service.get_any(db, number)
    messages = service.messages_after(db, conversation, after_id)
    if any(m.sender_role == SenderRole.customer and m.read_at is None for m in messages):
        service.mark_read(db, conversation, SenderRole.store)
        db.commit()
    return NewMessages(
        status=conversation.status,
        messages=message_responses(db, messages),
        last_message_id=messages[-1].id if messages else after_id,
    )


@router.post(
    "/support/conversations/{number}/messages",
    status_code=status.HTTP_201_CREATED,
    summary="Reply as the store",
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "conversation_closed"},
        422: {"model": ErrorResponse, "description": "message_empty / message_too_long"},
    },
)
def reply(number: str, data: MessageCreate, admin: AdminUser, db: DbSession) -> MessageResponse:
    conversation = service.get_any(db, number)
    try:
        message = service.send(db, conversation, admin, SenderRole.store, data.body)
    except Exception:
        db.rollback()
        raise
    db.commit()
    return message_responses(db, [message])[0]


@router.post(
    "/support/conversations/{number}/close", summary="Close a conversation", responses=NOT_FOUND
)
def close_conversation(number: str, db: DbSession) -> AdminConversationDetail:
    conversation = service.get_any(db, number)
    service.close(db, conversation)
    db.commit()
    return _detail(db, conversation)


@router.post(
    "/support/conversations/{number}/reopen", summary="Reopen a conversation", responses=NOT_FOUND
)
def reopen_conversation(number: str, db: DbSession) -> AdminConversationDetail:
    conversation = service.get_any(db, number)
    service.reopen(db, conversation)
    db.commit()
    return _detail(db, conversation)
