"""Customer support conversations (the customer's own only).

Messages sent here are always `customer` messages: the role comes from the
endpoint, so a customer can never post as the store.
"""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAuth, DbSession
from app.core import rate_limit
from app.models import SenderRole, SupportConversation, SupportMessage
from app.schemas.catalog import ErrorResponse
from app.schemas.support import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationSummary,
    MessageCreate,
    MessageResponse,
    NewMessages,
    UnreadCount,
)
from app.services import support as service
from app.services.errors import ServiceError

router = APIRouter(prefix="/support", tags=["support"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "conversation_not_found"}}
MESSAGE_ERRORS = {
    409: {"model": ErrorResponse, "description": "conversation_closed"},
    422: {"model": ErrorResponse, "description": "message_empty / message_too_long"},
    429: {"model": ErrorResponse, "description": "too_many_messages"},
}


def message_responses(db, messages: list[SupportMessage]) -> list[MessageResponse]:
    names = service.sender_names(db, messages)
    return [
        MessageResponse(
            id=m.id,
            sender_role=m.sender_role,
            sender_name=service.STORE_NAME
            if m.sender_role == SenderRole.store
            else names.get(m.sender_user_id, "Customer"),
            body=m.body,
            created_at=m.created_at,
            read_at=m.read_at,
        )
        for m in messages
    ]


def summary_fields(entry: dict) -> dict:
    conversation: SupportConversation = entry["conversation"]
    last = entry["last_message"]
    return {
        "conversation_number": conversation.conversation_number,
        "subject": conversation.subject,
        "subject_label": service.SUBJECT_LABELS[conversation.subject],
        "status": conversation.status,
        "order_number": entry["order_number"],
        "return_number": entry["return_number"],
        "last_message_preview": last.body[:140] if last else None,
        "last_message_role": last.sender_role if last else None,
        "last_message_at": conversation.last_message_at,
        "unread_count": entry["unread"],
        "created_at": conversation.created_at,
    }


def entry_for(db, conversation: SupportConversation, reader: SenderRole) -> dict:
    """The list-style summary data for one conversation."""
    rows = db.execute(
        service._base_query(reader).where(SupportConversation.id == conversation.id)
    ).all()
    return service._attach_last_messages(db, rows)[0]


def check_rate(user_id: int) -> None:
    key = str(user_id)
    if (wait := rate_limit.support_messages_by_user.retry_after(key)) is not None:
        raise ServiceError(
            429,
            "too_many_messages",
            "You're sending messages very quickly. Please wait a moment.",
            retry_after=wait,
        )
    rate_limit.support_messages_by_user.hit(key)


def _detail(db, conversation: SupportConversation) -> ConversationDetail:
    service.mark_read(db, conversation, SenderRole.customer)
    db.commit()
    messages = service.messages_after(db, conversation)
    return ConversationDetail(
        **summary_fields(entry_for(db, conversation, SenderRole.customer)),
        closed_at=conversation.closed_at,
        messages=message_responses(db, messages),
        last_message_id=messages[-1].id if messages else 0,
    )


@router.get("/conversations", summary="My support conversations, latest activity first")
def list_conversations(
    current: CurrentAuth,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationList:
    entries, total = service.list_for_user(db, current.user, limit, offset)
    return ConversationList(
        items=[ConversationSummary(**summary_fields(e)) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    summary="Start a conversation, optionally about one of my orders or returns",
    responses={
        404: {"model": ErrorResponse, "description": "order_not_found / return_not_found"},
        422: {"model": ErrorResponse, "description": "message_empty / message_too_long"},
    },
)
def create_conversation(
    data: ConversationCreate, current: CurrentAuth, db: DbSession
) -> ConversationDetail:
    check_rate(current.user.id)
    try:
        conversation = service.create(
            db, current.user, data.subject, data.message, data.order_number, data.return_number
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    return _detail(db, conversation)


@router.get("/unread-count", summary="Store messages I haven't read yet")
def unread_count(current: CurrentAuth, db: DbSession) -> UnreadCount:
    return UnreadCount(unread=service.unread_for_user(db, current.user))


@router.get(
    "/conversations/{number}",
    summary="One of my conversations (marks store messages as read)",
    responses=NOT_FOUND,
)
def read_conversation(number: str, current: CurrentAuth, db: DbSession) -> ConversationDetail:
    return _detail(db, service.get_for_user(db, current.user, number))


@router.get(
    "/conversations/{number}/messages",
    summary="Polling: messages after a given id",
    responses=NOT_FOUND,
)
def new_messages(
    number: str,
    current: CurrentAuth,
    db: DbSession,
    after_id: Annotated[int, Query(ge=0)] = 0,
) -> NewMessages:
    conversation = service.get_for_user(db, current.user, number)
    messages = service.messages_after(db, conversation, after_id)
    if any(m.sender_role == SenderRole.store and m.read_at is None for m in messages):
        service.mark_read(db, conversation, SenderRole.customer)
        db.commit()
    return NewMessages(
        status=conversation.status,
        messages=message_responses(db, messages),
        last_message_id=messages[-1].id if messages else after_id,
    )


@router.post(
    "/conversations/{number}/messages",
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    responses={**NOT_FOUND, **MESSAGE_ERRORS},
)
def send_message(
    number: str, data: MessageCreate, current: CurrentAuth, db: DbSession
) -> MessageResponse:
    conversation = service.get_for_user(db, current.user, number)
    check_rate(current.user.id)
    try:
        message = service.send(db, conversation, current.user, SenderRole.customer, data.body)
    except Exception:
        db.rollback()
        raise
    db.commit()
    return message_responses(db, [message])[0]


@router.post("/conversations/{number}/close", summary="Close my conversation", responses=NOT_FOUND)
def close_conversation(number: str, current: CurrentAuth, db: DbSession) -> ConversationDetail:
    conversation = service.get_for_user(db, current.user, number)
    service.close(db, conversation)
    db.commit()
    return _detail(db, conversation)


@router.post(
    "/conversations/{number}/reopen", summary="Reopen my conversation", responses=NOT_FOUND
)
def reopen_conversation(number: str, current: CurrentAuth, db: DbSession) -> ConversationDetail:
    conversation = service.get_for_user(db, current.user, number)
    service.reopen(db, conversation)
    db.commit()
    return _detail(db, conversation)
