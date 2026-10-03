"""Registration, login, tokens, sessions and logout, against PostgreSQL."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import JWT_ALGORITHM, settings
from app.models import AuthSession, Role, User

PASSWORD = "plantain market morning"
NEW_PASSWORD = "douala rain season 2026"


def register(client, email="alex@example.com", password=PASSWORD, **extra):
    payload = {
        "email": email,
        "password": password,
        "first_name": "Alex",
        "last_name": "Tadji",
        **extra,
    }
    return client.post("/api/v1/auth/register", json=payload)


def login(client, email="alex@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def me(client, token: str):
    return client.get("/api/v1/users/me", headers=bearer(token))


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def assert_no_secrets(body: object) -> None:
    text = str(body).lower()
    assert "password" not in text and "argon2" not in text


# Registration


def test_register_creates_signed_in_customer(client, db_session):
    response = register(client, phone="+237 6 99 11 22 33")
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "customer"
    assert body["user"]["is_verified"] is False
    assert body["user"]["profile"] == {
        "first_name": "Alex",
        "last_name": "Tadji",
        "phone": "+237699112233",
        "avatar_path": None,
    }
    assert body["token_type"] == "bearer" and body["access_token"] and body["refresh_token"]
    assert me(client, body["access_token"]).status_code == 200
    assert_no_secrets(body["user"])


def test_register_normalizes_email(client):
    body = register(client, email="  Alex.Tadji@Example.COM ").json()
    assert body["user"]["email"] == "alex.tadji@example.com"
    assert login(client, email="ALEX.TADJI@example.com").status_code == 200


def test_register_rejects_duplicate_email_case_insensitively(client):
    assert register(client).status_code == 201
    response = register(client, email="ALEX@example.com")
    assert response.status_code == 409
    assert error_code(response) == "email_already_registered"


def test_password_is_stored_as_argon2_hash(client, db_session):
    register(client)
    user = db_session.scalar(select(User).where(User.email == "alex@example.com"))
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


@pytest.mark.parametrize("field", [{"role": "admin"}, {"is_active": True}, {"is_verified": True}])
def test_public_registration_cannot_set_privileged_fields(client, db_session, field):
    response = register(client, **field)
    assert response.status_code == 422
    assert db_session.scalar(select(User).where(User.role == Role.admin)) is None


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"email": "not-an-email"}, "email"),
        ({"password": "short"}, "password"),
        ({"password": " " * 12}, "password"),
        ({"password": "x" * 129}, "password"),
        ({"first_name": "   "}, "first_name"),
        ({"phone": "call me"}, "phone"),
    ],
)
def test_register_validation_errors_are_structured(client, overrides, field):
    response = register(client, **overrides)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert field in detail["fields"]


def test_long_passphrase_is_accepted_without_truncation(client):
    passphrase = "a" * 100 + " tail"
    assert register(client, password=passphrase).status_code == 201
    assert login(client, password="a" * 100).status_code == 401


# Login


def test_login_success_updates_last_login(client, db_session):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "alex@example.com"
    user = db_session.scalar(select(User).where(User.email == "alex@example.com"))
    assert user.last_login_at is not None


def test_wrong_password_and_unknown_email_fail_identically(client):
    register(client)
    wrong = login(client, password="wrong password here")
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert (
        wrong.json()
        == unknown.json()
        == {"detail": {"code": "invalid_credentials", "message": "Email or password is incorrect."}}
    )


def test_inactive_account_cannot_log_in(client, db_session):
    token = register(client).json()["access_token"]
    db_session.scalar(select(User).where(User.email == "alex@example.com")).is_active = False
    db_session.flush()
    response = login(client)
    assert response.status_code == 403
    assert error_code(response) == "inactive_account"
    assert me(client, token).status_code == 401


def test_repeated_failed_logins_are_rate_limited(client):
    register(client)
    for _ in range(5):
        assert login(client, password="wrong password here").status_code == 401
    response = login(client)  # even the right password is refused for now
    assert response.status_code == 429
    assert error_code(response) == "too_many_attempts"
    assert int(response.headers["Retry-After"]) > 0


# Protected routes and tokens


def test_protected_route_requires_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert error_code(response) == "authentication_required"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def _token(claims: dict, lifetime: timedelta, key: str | None = None) -> str:
    now = datetime.now(UTC)
    payload = {**claims, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, key or settings.jwt_secret(), algorithm=JWT_ALGORITHM)


def test_expired_access_token_is_rejected(client):
    body = register(client).json()
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    expired = _token(
        {"sub": claims["sub"], "sid": claims["sid"], "type": "access"}, timedelta(seconds=-5)
    )
    response = me(client, expired)
    assert response.status_code == 401
    assert error_code(response) == "invalid_token"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        "a.b.c",
        _token({"sub": "1", "sid": "x", "type": "access"}, timedelta(minutes=5), "y" * 40),
    ],
    ids=["garbage", "malformed", "wrong-signature"],
)
def test_malformed_or_forged_tokens_are_rejected(client, token):
    assert me(client, token).status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client):
    body = register(client).json()
    assert me(client, body["refresh_token"]).status_code == 401


def test_refresh_rotates_tokens(client):
    body = register(client).json()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != body["refresh_token"]
    assert me(client, rotated["access_token"]).status_code == 200


def test_reusing_an_old_refresh_token_revokes_the_session(client):
    body = register(client).json()
    rotated = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    ).json()
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert reuse.status_code == 401
    assert error_code(reuse) == "invalid_refresh_token"
    # The legitimate (newer) tokens of that session stop working too.
    assert me(client, rotated["access_token"]).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
        ).status_code
        == 401
    )


def test_expired_refresh_token_is_rejected(client):
    body = register(client).json()
    claims = jwt.decode(body["refresh_token"], options={"verify_signature": False})
    expired = _token({**claims}, timedelta(seconds=-5))
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": expired})
    assert response.status_code == 401


def test_logout_revokes_session_immediately(client, db_session):
    body = register(client).json()
    response = client.post("/api/v1/auth/logout", json={"refresh_token": body["refresh_token"]})
    assert response.status_code == 204
    assert me(client, body["access_token"]).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
        ).status_code
        == 401
    )
    session = db_session.scalar(select(AuthSession))
    assert session.revoked_at is not None


def test_logout_with_bad_token_is_harmless(client):
    assert client.post("/api/v1/auth/logout", json={"refresh_token": "nope"}).status_code == 204


def test_each_login_is_a_separate_session(client):
    register(client)
    first = login(client).json()
    second = login(client).json()
    client.post("/api/v1/auth/logout", json={"refresh_token": first["refresh_token"]})
    assert me(client, first["access_token"]).status_code == 401
    assert me(client, second["access_token"]).status_code == 200
