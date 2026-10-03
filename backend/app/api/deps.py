"""Shared FastAPI dependencies."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import AuthSession, User
from app.services import auth
from app.services.auth import AuthError

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/login")


@dataclass
class Authenticated:
    user: User
    session: AuthSession


def get_authenticated(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Authenticated:
    """Requires `Authorization: Bearer <access token>` for an active session."""
    if credentials is None:
        raise AuthError(401, "authentication_required", "Please log in to continue.")
    user, session = auth.user_from_access_token(db, credentials.credentials)
    return Authenticated(user=user, session=session)


CurrentAuth = Annotated[Authenticated, Depends(get_authenticated)]


def client_ip(request: Request) -> str:
    """The caller's IP. X-Forwarded-For is trusted only from the configured proxies
    (the local Next.js server), because anyone else could set it to anything."""
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and peer in settings.trusted_proxy_ips:
        return forwarded.split(",")[0].strip() or peer
    return peer
