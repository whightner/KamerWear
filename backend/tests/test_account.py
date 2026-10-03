"""Current user, profile updates, password change and admin creation."""

import pytest
from sqlalchemy import select

from app.db import create_admin as create_admin_cmd
from app.db.create_admin import AdminCreationError, create_admin
from app.models import Role, User
from tests.test_auth import NEW_PASSWORD, PASSWORD, bearer, error_code, login, me, register


@pytest.fixture
def account(client):
    return register(client, phone="+237699112233").json()


def test_get_current_user(client, account):
    response = me(client, account["access_token"])
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "email", "role", "is_active", "is_verified", "created_at", "profile"}
    assert body["profile"]["first_name"] == "Alex"


def test_update_allowed_profile_fields(client, account):
    response = client.patch(
        "/api/v1/users/me",
        json={"first_name": "  Alexandra ", "phone": "+237 677 00 11 22"},
        headers=bearer(account["access_token"]),
    )
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["first_name"] == "Alexandra"
    assert profile["last_name"] == "Tadji"  # untouched
    assert profile["phone"] == "+237677001122"


def test_phone_can_be_cleared(client, account):
    response = client.patch(
        "/api/v1/users/me", json={"phone": None}, headers=bearer(account["access_token"])
    )
    assert response.json()["profile"]["phone"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "admin"},
        {"is_active": False},
        {"is_verified": True},
        {"email": "new@example.com"},
        {"password_hash": "x"},
    ],
)
def test_privileged_fields_cannot_be_changed(client, db_session, account, payload):
    response = client.patch(
        "/api/v1/users/me", json=payload, headers=bearer(account["access_token"])
    )
    assert response.status_code == 422
    user = db_session.scalar(select(User).where(User.email == "alex@example.com"))
    assert (user.role, user.is_active, user.is_verified) == (Role.customer, True, False)


def test_profile_requires_authentication(client):
    assert client.patch("/api/v1/users/me", json={"first_name": "X"}).status_code == 401


def test_change_password_success_signs_out_other_sessions(client, account):
    other = login(client).json()
    response = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers=bearer(account["access_token"]),
    )
    assert response.status_code == 204
    assert me(client, account["access_token"]).status_code == 200  # this session stays
    assert me(client, other["access_token"]).status_code == 401  # others are signed out
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password=NEW_PASSWORD).status_code == 200


def test_change_password_rejects_wrong_current_password(client, account):
    response = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "not my password", "new_password": NEW_PASSWORD},
        headers=bearer(account["access_token"]),
    )
    assert response.status_code == 400
    assert error_code(response) == "invalid_current_password"
    assert login(client, password=PASSWORD).status_code == 200


def test_change_password_applies_policy(client, account):
    response = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=bearer(account["access_token"]),
    )
    assert response.status_code == 422
    assert "new_password" in response.json()["detail"]["fields"]


# Admin creation command


def test_create_admin_creates_admin(db_session):
    user = create_admin(db_session, " Admin@KamerWear.cm ", NEW_PASSWORD, "Ada", "Admin")
    assert user.role == Role.admin
    assert user.email == "admin@kamerwear.cm"
    assert user.password_hash.startswith("$argon2id$")


def test_create_admin_refuses_existing_email(client, db_session, account):
    with pytest.raises(AdminCreationError, match="already exists"):
        create_admin(db_session, "alex@example.com", NEW_PASSWORD, "Ada", "Admin")
    user = db_session.scalar(select(User).where(User.email == "alex@example.com"))
    assert user.role == Role.customer


def test_create_admin_applies_password_policy(db_session):
    with pytest.raises(AdminCreationError, match="at least 10"):
        create_admin(db_session, "admin@kamerwear.cm", "short", "Ada", "Admin")


def test_create_admin_command_needs_input(monkeypatch, capsys):
    for name in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN_FIRST_NAME", "ADMIN_LAST_NAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert create_admin_cmd.main() == 1
    assert "Set ADMIN_EMAIL" in capsys.readouterr().err


def test_create_admin_command_with_env(monkeypatch, capsys, db_session):
    from sqlalchemy.orm import Session

    # A real session that is closed when the command finishes, as in production.
    monkeypatch.setattr(
        create_admin_cmd,
        "SessionLocal",
        lambda: Session(bind=db_session.connection(), join_transaction_mode="create_savepoint"),
    )
    monkeypatch.setenv("ADMIN_EMAIL", "owner@kamerwear.cm")
    monkeypatch.setenv("ADMIN_FIRST_NAME", "Store")
    monkeypatch.setenv("ADMIN_LAST_NAME", "Owner")
    monkeypatch.setenv("ADMIN_PASSWORD", NEW_PASSWORD)
    assert create_admin_cmd.main() == 0
    assert "Created admin account owner@kamerwear.cm" in capsys.readouterr().out
    assert NEW_PASSWORD not in capsys.readouterr().out
    user = db_session.scalar(select(User).where(User.email == "owner@kamerwear.cm"))
    assert user.role == Role.admin
