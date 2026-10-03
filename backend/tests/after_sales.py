"""Helpers for the returns and support tests."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import Order, OrderStatus
from tests.commerce import add_address, add_to_cart, place_order, variant

STEPS = ("confirmed", "preparing", "shipped", "out_for_delivery", "delivered")


def advance(client, admin, number, until="delivered"):
    for status in STEPS:
        response = client.post(
            f"/api/v1/admin/orders/{number}/status", json={"status": status}, headers=admin
        )
        assert response.status_code == 200, response.text
        if status == until:
            return


def new_order(client, db, headers, lines=(("CHT-BLACK-M", 2), ("CHT-RED-L", 1))) -> str:
    address = add_address(client, headers)
    for sku, quantity in lines:
        assert add_to_cart(client, headers, variant(db, sku).id, quantity).status_code in (200, 201)
    response = place_order(client, headers, address["id"])
    assert response.status_code == 201, response.text
    return response.json()["order_number"]


def order_items(db, number) -> dict[str, int]:
    """SKU -> order_item_id."""
    order = db.scalar(select(Order).where(Order.order_number == number))
    return {item.sku: item.id for item in order.items}


def age_delivery(db, number, days: int) -> None:
    """Pretends the delivery happened `days` ago."""
    order = db.scalar(select(Order).where(Order.order_number == number))
    for event in order.status_history:
        if event.status == OrderStatus.delivered:
            event.created_at = event.created_at - timedelta(days=days)
    db.flush()


@pytest.fixture
def delivered_order(client, db_session, customer, admin) -> str:
    """A delivered order of 2 x CHT-BLACK-M and 1 x CHT-RED-L."""
    number = new_order(client, db_session, customer)
    advance(client, admin, number)
    return number
