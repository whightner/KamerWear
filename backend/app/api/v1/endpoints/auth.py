from fastapi import APIRouter, Request, Response, status

from app.api.deps import DbSession, client_ip
from app.api.errors import api_error
from app.core import rate_limit
from app.core.config import settings
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.schemas.catalog import ErrorResponse
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user: User, access: str, refresh: str) -> AuthResponse:
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access,
        refresh_token=refresh,
        access_token_expires_in=settings.access_token_expire_minutes * 60,
        refresh_token_expires_in=settings.refresh_token_expire_days * 24 * 3600,
    )


def _too_many_attempts(retry_after: int):
    return api_error(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "too_many_attempts",
        "Too many attempts. Please wait a few minutes and try again.",
        headers={"Retry-After": str(retry_after)},
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer account",
    description="Always creates a CUSTOMER account and signs it in. Returns tokens.",
    responses={409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def register(data: RegisterRequest, request: Request, db: DbSession) -> AuthResponse:
    ip_key = client_ip(request)
    if (wait := rate_limit.registrations_by_ip.retry_after(ip_key)) is not None:
        raise _too_many_attempts(wait)
    rate_limit.registrations_by_ip.hit(ip_key)

    user = auth.register(db, data)
    access, refresh = auth.start_session(db, user)
    db.commit()
    return _auth_response(user, access, refresh)


@router.post(
    "/login",
    summary="Log in with email and password",
    responses={
        401: {"model": ErrorResponse, "description": "invalid_credentials"},
        403: {"model": ErrorResponse, "description": "inactive_account"},
        429: {"model": ErrorResponse, "description": "too_many_attempts"},
    },
)
def login(data: LoginRequest, request: Request, db: DbSession) -> AuthResponse:
    email_key = auth.normalize_email(str(data.email))
    ip_key = client_ip(request)
    for limiter, key in (
        (rate_limit.login_failures_by_email, email_key),
        (rate_limit.login_failures_by_ip, ip_key),
    ):
        if (wait := limiter.retry_after(key)) is not None:
            raise _too_many_attempts(wait)

    try:
        user = auth.authenticate(db, str(data.email), data.password)
    except auth.AuthError:
        rate_limit.login_failures_by_email.hit(email_key)
        rate_limit.login_failures_by_ip.hit(ip_key)
        raise
    rate_limit.login_failures_by_email.reset(email_key)
    access, refresh = auth.start_session(db, user)
    db.commit()
    return _auth_response(user, access, refresh)


@router.post(
    "/refresh",
    summary="Exchange a refresh token for new tokens",
    description="Refresh tokens are single-use: each call returns a new pair. "
    "Reusing an old refresh token signs that session out.",
    responses={401: {"model": ErrorResponse}},
)
def refresh(data: RefreshRequest, db: DbSession) -> AuthResponse:
    try:
        user, access, new_refresh = auth.refresh_session(db, data.refresh_token)
    except auth.AuthError:
        db.commit()  # keep a revocation caused by refresh-token reuse
        raise
    db.commit()
    return _auth_response(user, access, new_refresh)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (revoke the session)",
    description="Revokes the session behind the refresh token. Always succeeds.",
)
def logout(data: RefreshRequest, db: DbSession) -> Response:
    auth.end_session(db, data.refresh_token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
