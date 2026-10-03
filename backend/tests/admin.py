"""Helpers for the admin API tests."""

import pytest

from app.db.create_admin import create_admin
from tests.commerce import add_address, add_to_cart, place_order, signup, variant
from tests.test_auth import PASSWORD, bearer, login

ADMIN_EMAIL = "staff@kamerwear.cm"


@pytest.fixture
def admin(client, db_session) -> dict[str, str]:
    create_admin(db_session, ADMIN_EMAIL, PASSWORD, "Store", "Admin")
    response = login(client, email=ADMIN_EMAIL)
    assert response.status_code == 200, response.text
    return bearer(response.json()["access_token"])


@pytest.fixture
def customer(client) -> dict[str, str]:
    return signup(client, "alex@example.com")


@pytest.fixture
def placed_order(client, db_session, customer) -> str:
    """A pending order of 2 x CHT-BLACK-M (Douala) placed by the customer."""
    address = add_address(client, customer)
    add_to_cart(client, customer, variant(db_session, "CHT-BLACK-M").id, 2)
    response = place_order(client, customer, address["id"])
    assert response.status_code == 201, response.text
    return response.json()["order_number"]
