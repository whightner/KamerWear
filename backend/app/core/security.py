"""Password hashing (Argon2id) and JWT access/refresh tokens (PyJWT, HS256)."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import JWT_ALGORITHM, settings

# argon2-cffi's defaults follow the RFC 9106 "low memory" profile (Argon2id).
_hasher = PasswordHasher()

# Verified against when the email is unknown, so a login attempt takes about the
# same time whether or not the account exists.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """True if the password matches. Never raises for a wrong password or bad hash."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and bool(password_hash)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    session_id: str
    token_type: TokenType
    jti: str | None


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired, or of the wrong type."""


def _encode(claims: dict, lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {**claims, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.jwt_secret(), algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int, session_id: str) -> str:
    return _encode(
        {"sub": str(user_id), "sid": session_id, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: int, session_id: str, jti: str) -> str:
    return _encode(
        {"sub": str(user_id), "sid": session_id, "type": "refresh", "jti": jti},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "sid", "type"]},
        )
        if payload["type"] != expected_type:
            raise InvalidTokenError("wrong token type")
        return TokenClaims(
            user_id=int(payload["sub"]),
            session_id=str(payload["sid"]),
            token_type=expected_type,
            jti=payload.get("jti"),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidTokenError(str(exc)) from exc
