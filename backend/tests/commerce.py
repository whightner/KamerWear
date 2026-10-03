"""Helpers shared by the address, cart, checkout and order tests."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Inventory, ProductVariant
from tests.test_auth import bearer, register

ADDRESS = {
    "label": "Home",
    "recipient_name": "Alex Tadji",
    "phone": "+237 6 99 11 22 33",
    "region": "Littoral",
    "city": "Douala",
    "quarter": "Bonamoussadi",
    "street_or_landmark": "Near Tradex, blue gate",
}


def signup(client, email: str) -> dict[str, str]:
    """Registers a customer and returns their auth header."""
    response = register(client, email=email)
    assert response.status_code == 201, response.text
    return bearer(response.json()["access_token"])


def variant(db: Session, sku: str) -> ProductVariant:
    return db.scalar(select(ProductVariant).where(ProductVariant.sku == sku))


def set_stock(db: Session, sku: str, on_hand: int, reserved: int = 0) -> None:
    inventory = db.scalar(
        select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku)
    )
    inventory.on_hand = on_hand
    inventory.reserved = reserved
    db.flush()


def add_address(client, headers, **changes) -> dict:
    response = client.post("/api/v1/addresses", json={**ADDRESS, **changes}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def add_to_cart(client, headers, variant_id: int, quantity: int = 1):
    return client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant_id, "quantity": quantity},
        headers=headers,
    )


def place_order(client, headers, address_id: int, key: str | None = None, **extra):
    return client.post(
        "/api/v1/orders",
        json={"address_id": address_id, "payment_method": "cash_on_delivery", **extra},
        headers={**headers, "Idempotency-Key": key or uuid.uuid4().hex},
    )
