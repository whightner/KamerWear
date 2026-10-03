"""Create an ADMIN account for development.

    python -m app.db.create_admin

Asks for the email, name and password (password input is hidden). For scripted
use, set ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_FIRST_NAME and ADMIN_LAST_NAME
instead. Nothing is hardcoded, and public registration can never create admins.
An existing email is never modified.
"""

import getpass
import os
import sys

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Role, User, UserProfile
from app.schemas.auth import RegisterRequest
from app.services.auth import normalize_email
from app.core.security import hash_password


class AdminCreationError(Exception):
    pass


def create_admin(db: Session, email: str, password: str, first_name: str, last_name: str) -> User:
    """Validates like registration (email, password policy, names), then creates an admin."""
    try:
        data = RegisterRequest(
            email=email, password=password, first_name=first_name, last_name=last_name
        )
    except ValidationError as exc:
        messages = "; ".join(err["msg"].removeprefix("Value error, ") for err in exc.errors())
        raise AdminCreationError(messages) from exc

    normalized = normalize_email(str(data.email))
    if db.scalar(select(User.id).where(User.email == normalized)) is not None:
        raise AdminCreationError(
            f"An account with {normalized} already exists; it was not changed."
        )

    user = User(
        email=normalized,
        password_hash=hash_password(data.password),
        role=Role.admin,
        is_active=True,
        is_verified=False,
        profile=UserProfile(first_name=data.first_name, last_name=data.last_name),
    )
    db.add(user)
    db.commit()
    return user


def _ask(env_name: str, prompt: str, secret: bool = False) -> str:
    value = os.environ.get(env_name)
    if value:
        return value
    if not sys.stdin.isatty():
        raise AdminCreationError(f"Set {env_name} or run this command interactively.")
    if secret:
        first = getpass.getpass(prompt)
        if first != getpass.getpass("Repeat password: "):
            raise AdminCreationError("Passwords do not match.")
        return first
    return input(prompt).strip()


def main() -> int:
    try:
        email = _ask("ADMIN_EMAIL", "Admin email: ")
        first_name = _ask("ADMIN_FIRST_NAME", "First name: ")
        last_name = _ask("ADMIN_LAST_NAME", "Last name: ")
        password = _ask("ADMIN_PASSWORD", "Password (min. 10 characters): ", secret=True)
        with SessionLocal() as db:
            user = create_admin(db, email, password, first_name, last_name)
            # Read while the session is open (attributes expire on commit).
            message = f"Created admin account {user.email} (id {user.id})."
    except AdminCreationError as exc:
        print(f"Admin not created: {exc}", file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
