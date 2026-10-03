"""Saved delivery addresses. Every query is scoped to the signed-in user."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Address, User
from app.schemas.address import AddressCreate, AddressUpdate
from app.services.errors import not_found


def address_not_found():
    return not_found("address_not_found", "This address doesn't exist or isn't yours.")


def list_addresses(db: Session, user: User) -> list[Address]:
    """Default address first, then newest first."""
    return list(
        db.scalars(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.is_default.desc(), Address.created_at.desc(), Address.id.desc())
        )
    )


def get_address(db: Session, user: User, address_id: int) -> Address:
    """The user's own address. Someone else's address looks exactly like a missing one."""
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    if address is None:
        raise address_not_found()
    return address


def _clear_default(db: Session, user: User) -> None:
    # Runs before the new default is written, so the partial unique index
    # ("one default per user") is never violated.
    db.execute(
        update(Address)
        .where(Address.user_id == user.id, Address.is_default.is_(True))
        .values(is_default=False)
    )


def create_address(db: Session, user: User, data: AddressCreate) -> Address:
    has_addresses = db.scalar(select(Address.id).where(Address.user_id == user.id).limit(1))
    # The first address is always the default.
    make_default = data.is_default or has_addresses is None
    if make_default:
        _clear_default(db, user)
    address = Address(user_id=user.id, **data.model_dump(exclude={"is_default"}))
    address.is_default = make_default
    db.add(address)
    db.flush()
    return address


def update_address(db: Session, user: User, address_id: int, data: AddressUpdate) -> Address:
    address = get_address(db, user, address_id)
    changes = data.model_dump(exclude_unset=True)
    make_default = changes.pop("is_default", None)
    for field in (
        "label",
        "recipient_name",
        "phone",
        "region",
        "city",
        "quarter",
        "street_or_landmark",
    ):
        # These are required; null means "leave unchanged".
        if changes.get(field, ...) is None:
            changes.pop(field)
    for field, value in changes.items():
        setattr(address, field, value)
    if make_default and not address.is_default:
        _clear_default(db, user)
        address.is_default = True
    db.flush()
    return address


def delete_address(db: Session, user: User, address_id: int) -> None:
    """Deletes the address. Orders keep their own copy of it.

    If it was the default, the most recently created remaining address
    becomes the default.
    """
    address = get_address(db, user, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        newest = db.scalar(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.created_at.desc(), Address.id.desc())
            .limit(1)
        )
        if newest is not None:
            newest.is_default = True
            db.flush()
