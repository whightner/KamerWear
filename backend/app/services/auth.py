"""Accounts, login sessions and tokens.

Session model: every login creates an AuthSession row. Access tokens (short-lived)
and refresh tokens (longer-lived, rotated on each use) both carry the session id,
and every authenticated request checks that the session is still active. So
logging out or changing the password takes effect immediately, not when the
token expires.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.models import AuthSession, Role, User, UserProfile
from app.schemas.auth import ChangePasswordRequest, ProfileUpdate, RegisterRequest


class AuthError(Exception):
    """An expected auth failure, turned into a structured HTTP error by the API layer."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def invalid_credentials() -> AuthError:
    return AuthError(401, "invalid_credentials", "Email or password is incorrect.")


def invalid_token() -> AuthError:
    return AuthError(401, "invalid_token", "Your session has expired. Please log in again.")


def invalid_refresh() -> AuthError:
    return AuthError(401, "invalid_refresh_token", "Your session has expired. Please log in again.")


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register(db: Session, data: RegisterRequest) -> User:
    """Creates a CUSTOMER with a profile. The role is never taken from the request."""
    email = normalize_email(str(data.email))
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise AuthError(
            409, "email_already_registered", "An account with this email already exists."
        )

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        role=Role.customer,
        is_active=True,
        is_verified=False,
        profile=UserProfile(first_name=data.first_name, last_name=data.last_name, phone=data.phone),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # two registrations racing for the same email
        db.rollback()
        raise AuthError(
            409, "email_already_registered", "An account with this email already exists."
        ) from exc
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Checks credentials. Unknown email and wrong password fail the same way."""
    user = db.scalar(
        select(User).where(User.email == normalize_email(email)).options(joinedload(User.profile))
    )
    # verify_password also runs (against a dummy hash) when the user is unknown.
    if not verify_password(user.password_hash if user else None, password) or user is None:
        raise invalid_credentials()
    if not user.is_active:
        raise AuthError(403, "inactive_account", "This account has been deactivated.")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = _now()
    return user


def _issue_tokens(user: User, session: AuthSession) -> tuple[str, str]:
    session.refresh_jti = secrets.token_urlsafe(24)
    session.last_used_at = _now()
    session.expires_at = _now() + timedelta(days=settings.refresh_token_expire_days)
    return (
        create_access_token(user.id, session.id),
        create_refresh_token(user.id, session.id, session.refresh_jti),
    )


def start_session(db: Session, user: User) -> tuple[str, str]:
    """Creates a session for a freshly authenticated user; returns (access, refresh)."""
    session = AuthSession(id=str(uuid.uuid4()), user_id=user.id, refresh_jti="", expires_at=_now())
    db.add(session)
    tokens = _issue_tokens(user, session)
    db.flush()
    return tokens


def _active_session(db: Session, session_id: str, user_id: int) -> AuthSession | None:
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id)
        .options(joinedload(AuthSession.user).joinedload(User.profile))
    )
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or session.expires_at <= _now()
        or not session.user.is_active
    ):
        return None
    return session


def refresh_session(db: Session, refresh_token: str) -> tuple[User, str, str]:
    """Rotates the refresh token. Reusing an old refresh token revokes the session."""
    try:
        claims = decode_token(refresh_token, "refresh")
    except InvalidTokenError as exc:
        raise invalid_refresh() from exc
    session = _active_session(db, claims.session_id, claims.user_id)
    if session is None:
        raise invalid_refresh()
    if claims.jti != session.refresh_jti:
        session.revoked_at = _now()
        db.flush()
        raise invalid_refresh()
    access, refresh = _issue_tokens(session.user, session)
    db.flush()
    return session.user, access, refresh


def end_session(db: Session, refresh_token: str) -> None:
    """Logout: revokes the session behind a refresh token. Quietly ignores bad tokens."""
    try:
        claims = decode_token(refresh_token, "refresh")
    except InvalidTokenError:
        return
    session = db.get(AuthSession, claims.session_id)
    if session is not None and session.user_id == claims.user_id and session.revoked_at is None:
        session.revoked_at = _now()
        db.flush()


def user_from_access_token(db: Session, access_token: str) -> tuple[User, AuthSession]:
    try:
        claims = decode_token(access_token, "access")
    except InvalidTokenError as exc:
        raise invalid_token() from exc
    session = _active_session(db, claims.session_id, claims.user_id)
    if session is None:
        raise invalid_token()
    return session.user, session


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    # first_name/last_name can't be cleared; sending phone: null clears the phone.
    for field in ("first_name", "last_name"):
        if changes.get(field) is not None:
            setattr(user.profile, field, changes[field])
    if "phone" in changes:
        user.profile.phone = changes["phone"]
    db.flush()
    return user


def change_password(
    db: Session, user: User, current_session_id: str, data: ChangePasswordRequest
) -> None:
    """Replaces the password and signs out every other session of this user."""
    if not verify_password(user.password_hash, data.current_password):
        raise AuthError(400, "invalid_current_password", "Your current password is incorrect.")
    user.password_hash = hash_password(data.new_password)
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.id != current_session_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    db.flush()
