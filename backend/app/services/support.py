"""Customer support conversations: plain-text messages stored in PostgreSQL.

Clients poll `messages after id N` while a conversation is open, so there is
no WebSocket server, Redis or external chat service. The sender role comes
from the endpoint used (customer or admin), never from the request body.
Message text is stored as typed and always rendered as escaped plain text.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import SUPPORT_MESSAGE_MAX_LENGTH
from app.models import (
    ConversationStatus,
    Order,
    ReturnRequest,
    SenderRole,
    SupportConversation,
    SupportMessage,
    SupportSubject,
    User,
    UserProfile,
)
from app.services.errors import ServiceError, not_found

_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
STORE_NAME = "KamerWear support"
PAGE = 200  # messages per load; polling only fetches new ones

SUBJECT_LABELS = {
    SupportSubject.sizing: "Sizing question",
    SupportSubject.delivery: "Delivery question",
    SupportSubject.order_issue: "Order issue",
    SupportSubject.return_question: "Return question",
    SupportSubject.other: "Other",
}


def conversation_not_found() -> ServiceError:
    return not_found("conversation_not_found", "We couldn't find this conversation.")


def _now() -> datetime:
    return datetime.now(UTC)


def new_conversation_number(db: Session) -> str:
    year = datetime.now().year
    while True:
        number = f"KS-{year}-{''.join(secrets.choice(_ALPHABET) for _ in range(6))}"
        taken = db.scalar(
            select(SupportConversation.id).where(SupportConversation.conversation_number == number)
        )
        if taken is None:
            return number


def clean_body(body: str) -> str:
    text = body.strip()
    if not text:
        raise ServiceError(422, "message_empty", "Please write a message.")
    if len(text) > SUPPORT_MESSAGE_MAX_LENGTH:
        raise ServiceError(
            422,
            "message_too_long",
            f"Messages can be at most {SUPPORT_MESSAGE_MAX_LENGTH} characters.",
            max_length=SUPPORT_MESSAGE_MAX_LENGTH,
        )
    return text


def create(
    db: Session,
    user: User,
    subject: SupportSubject,
    body: str,
    order_number: str | None = None,
    return_number: str | None = None,
) -> SupportConversation:
    """A new conversation, optionally linked to the customer's own order or return."""
    text = clean_body(body)
    order = request = None
    if order_number:
        order = db.scalar(
            select(Order).where(
                Order.order_number == order_number.strip().upper(), Order.user_id == user.id
            )
        )
        if order is None:
            raise not_found("order_not_found", "We couldn't find an order with this reference.")
    if return_number:
        request = db.scalar(
            select(ReturnRequest).where(
                ReturnRequest.return_number == return_number.strip().upper(),
                ReturnRequest.user_id == user.id,
            )
        )
        if request is None:
            raise not_found("return_not_found", "We couldn't find a return with this reference.")
        if order is not None and order.id != request.order_id:
            raise ServiceError(
                422, "conversation_link_mismatch", "This return belongs to a different order."
            )
        order_id = request.order_id
    else:
        order_id = order.id if order else None
    now = _now()
    conversation = SupportConversation(
        conversation_number=new_conversation_number(db),
        user_id=user.id,
        order_id=order_id,
        return_request_id=request.id if request else None,
        subject=subject,
        status=ConversationStatus.open,
        last_message_at=now,
        messages=[
            SupportMessage(
                sender_user_id=user.id,
                sender_role=SenderRole.customer,
                body=text,
                created_at=now,
            )
        ],
    )
    db.add(conversation)
    db.flush()
    return conversation


def _unread(reader: SenderRole):
    """Correlated count of messages from the other side not read yet."""
    other = SenderRole.store if reader == SenderRole.customer else SenderRole.customer
    return (
        select(func.count(SupportMessage.id))
        .where(
            SupportMessage.conversation_id == SupportConversation.id,
            SupportMessage.sender_role == other,
            SupportMessage.read_at.is_(None),
        )
        .scalar_subquery()
    )


def _base_query(reader: SenderRole):
    last_id = (
        select(func.max(SupportMessage.id))
        .where(SupportMessage.conversation_id == SupportConversation.id)
        .scalar_subquery()
    )
    return (
        select(
            SupportConversation,
            Order.order_number,
            ReturnRequest.return_number,
            last_id.label("last_id"),
            _unread(reader).label("unread"),
        )
        .outerjoin(Order, Order.id == SupportConversation.order_id)
        .outerjoin(ReturnRequest, ReturnRequest.id == SupportConversation.return_request_id)
    )


def _attach_last_messages(db: Session, rows) -> list[dict]:
    last_ids = [row.last_id for row in rows if row.last_id]
    messages = (
        {m.id: m for m in db.scalars(select(SupportMessage).where(SupportMessage.id.in_(last_ids)))}
        if last_ids
        else {}
    )
    return [
        {
            "conversation": row[0],
            "order_number": row.order_number,
            "return_number": row.return_number,
            "last_message": messages.get(row.last_id),
            "unread": row.unread,
        }
        for row in rows
    ]


def list_for_user(db: Session, user: User, limit: int, offset: int) -> tuple[list[dict], int]:
    query = _base_query(SenderRole.customer).where(SupportConversation.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(SupportConversation.last_message_at.desc(), SupportConversation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return _attach_last_messages(db, rows), total


def list_all(
    db: Session,
    *,
    q: str | None,
    status: ConversationStatus | None,
    unread_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[tuple[dict, User]], int]:
    query = (
        _base_query(SenderRole.store)
        .add_columns(User)
        .join(User, User.id == SupportConversation.user_id)
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.outerjoin(UserProfile, UserProfile.user_id == User.id).where(
            or_(
                SupportConversation.conversation_number.ilike(pattern),
                Order.order_number.ilike(pattern),
                ReturnRequest.return_number.ilike(pattern),
                User.email.ilike(pattern),
                (UserProfile.first_name + " " + UserProfile.last_name).ilike(pattern),
            )
        )
    if status is not None:
        query = query.where(SupportConversation.status == status)
    if unread_only:
        query = query.where(_unread(SenderRole.store) > 0)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.options(joinedload(User.profile))
        .order_by(SupportConversation.last_message_at.desc(), SupportConversation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    entries = _attach_last_messages(db, rows)
    return [(entry, row[-1]) for entry, row in zip(entries, rows, strict=True)], total


def get_for_user(db: Session, user: User, number: str) -> SupportConversation:
    conversation = db.scalar(
        select(SupportConversation).where(
            SupportConversation.conversation_number == number.strip().upper(),
            SupportConversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise conversation_not_found()
    return conversation


def get_any(db: Session, number: str) -> SupportConversation:
    conversation = db.scalar(
        select(SupportConversation)
        .where(SupportConversation.conversation_number == number.strip().upper())
        .execution_options(populate_existing=True)
    )
    if conversation is None:
        raise conversation_not_found()
    return conversation


def messages_after(
    db: Session, conversation: SupportConversation, after_id: int = 0
) -> list[SupportMessage]:
    """New messages only (polling), oldest first. A first load gets the latest PAGE."""
    query = select(SupportMessage).where(SupportMessage.conversation_id == conversation.id)
    if after_id:
        return list(
            db.scalars(
                query.where(SupportMessage.id > after_id).order_by(SupportMessage.id).limit(PAGE)
            )
        )
    latest = db.scalars(query.order_by(SupportMessage.id.desc()).limit(PAGE)).all()
    return list(reversed(latest))


def mark_read(db: Session, conversation: SupportConversation, reader: SenderRole) -> None:
    other = SenderRole.store if reader == SenderRole.customer else SenderRole.customer
    db.execute(
        update(SupportMessage)
        .where(
            SupportMessage.conversation_id == conversation.id,
            SupportMessage.sender_role == other,
            SupportMessage.read_at.is_(None),
        )
        .values(read_at=_now())
    )


def send(
    db: Session, conversation: SupportConversation, sender: User, role: SenderRole, body: str
) -> SupportMessage:
    text = clean_body(body)
    db.refresh(conversation, with_for_update=True)
    if conversation.status == ConversationStatus.closed:
        raise ServiceError(
            409,
            "conversation_closed",
            "This conversation is closed. Reopen it or start a new one to send a message.",
        )
    now = _now()
    message = SupportMessage(
        conversation_id=conversation.id,
        sender_user_id=sender.id,
        sender_role=role,
        body=text,
        created_at=now,
    )
    db.add(message)
    conversation.last_message_at = now
    db.flush()
    return message


def close(db: Session, conversation: SupportConversation) -> None:
    db.refresh(conversation, with_for_update=True)
    if conversation.status != ConversationStatus.closed:
        conversation.status = ConversationStatus.closed
        conversation.closed_at = _now()
    db.flush()


def reopen(db: Session, conversation: SupportConversation) -> None:
    db.refresh(conversation, with_for_update=True)
    conversation.status = ConversationStatus.open
    conversation.closed_at = None
    db.flush()


def unread_for_user(db: Session, user: User) -> int:
    return (
        db.scalar(
            select(func.count(SupportMessage.id))
            .join(SupportConversation, SupportConversation.id == SupportMessage.conversation_id)
            .where(
                SupportConversation.user_id == user.id,
                SupportMessage.sender_role == SenderRole.store,
                SupportMessage.read_at.is_(None),
            )
        )
        or 0
    )


def conversations_needing_reply(db: Session) -> int:
    """Conversations with customer messages the store hasn't read."""
    return (
        db.scalar(
            select(func.count(func.distinct(SupportMessage.conversation_id))).where(
                SupportMessage.sender_role == SenderRole.customer,
                SupportMessage.read_at.is_(None),
            )
        )
        or 0
    )


def sender_names(db: Session, messages: list[SupportMessage]) -> dict[int, str]:
    """Customer first names for customer messages; store messages are 'KamerWear support'."""
    ids = {m.sender_user_id for m in messages if m.sender_role == SenderRole.customer}
    ids.discard(None)
    if not ids:
        return {}
    rows = db.execute(
        select(UserProfile.user_id, UserProfile.first_name).where(UserProfile.user_id.in_(ids))
    ).all()
    return dict(rows)
