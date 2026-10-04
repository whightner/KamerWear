"""One place that checks the authorization matrix end to end.

Customer A must never read or change customer B's data, and customers can't use
any admin endpoint. Ownership always comes from the access token.
"""

import re

import pytest

from app.main import app
from tests.after_sales import advance, new_order, order_items
from tests.commerce import add_address, add_to_cart, signup, variant
from tests.test_auth import error_code


@pytest.fixture
def b_data(client, db_session, admin):
    """Customer B with an address, a cart line, a delivered order, a return and a conversation."""
    b = signup(client, "b-owner@example.com")
    address = add_address(client, b)
    number = new_order(client, db_session, b, lines=(("CHT-BLACK-M", 1),))
    advance(client, admin, number)
    item = order_items(db_session, number)["CHT-BLACK-M"]
    ret = client.post(
        "/api/v1/returns",
        json={
            "order_number": number,
            "items": [{"order_item_id": item, "quantity": 1, "reason": "wrong_size"}],
        },
        headers=b,
    ).json()["return_number"]
    conv = client.post(
        "/api/v1/support/conversations",
        json={"subject": "other", "message": "Private question"},
        headers=b,
    ).json()["conversation_number"]
    add_to_cart(client, b, variant(db_session, "CHT-RED-L").id, 1)
    cart_item = client.get("/api/v1/cart", headers=b).json()["items"][0]["cart_item_id"]
    return {
        "headers": b,
        "address": address["id"],
        "order": number,
        "return": ret,
        "conversation": conv,
        "cart_item": cart_item,
    }


def test_customer_a_cannot_touch_customer_b(client, customer, b_data):
    a = customer
    attempts = [
        ("get", f"/api/v1/orders/{b_data['order']}", None),  # detail and tracking
        ("get", f"/api/v1/orders/{b_data['order']}/return-eligibility", None),
        ("patch", f"/api/v1/addresses/{b_data['address']}", {"label": "Mine now"}),
        ("delete", f"/api/v1/addresses/{b_data['address']}", None),
        ("get", f"/api/v1/returns/{b_data['return']}", None),
        ("post", f"/api/v1/returns/{b_data['return']}/cancel", None),
        ("get", f"/api/v1/support/conversations/{b_data['conversation']}", None),
        ("get", f"/api/v1/support/conversations/{b_data['conversation']}/messages", None),
        (
            "post",
            f"/api/v1/support/conversations/{b_data['conversation']}/messages",
            {"body": "hi"},
        ),
        ("post", f"/api/v1/support/conversations/{b_data['conversation']}/close", None),
        ("patch", f"/api/v1/cart/items/{b_data['cart_item']}", {"quantity": 3}),
        ("delete", f"/api/v1/cart/items/{b_data['cart_item']}", None),
    ]
    for method, path, body in attempts:
        kwargs = {"headers": a}
        if body is not None:
            kwargs["json"] = body
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 404, (method, path, response.status_code)

    # A's own views contain nothing of B's.
    me = client.get("/api/v1/users/me", headers=a).json()
    assert me["email"] == "alex@example.com"
    for path in ("/api/v1/addresses", "/api/v1/returns", "/api/v1/support/conversations"):
        body = client.get(path, headers=a).json()
        items = body if isinstance(body, list) else body["items"]
        assert items == [], path
    assert client.get("/api/v1/orders", headers=a).json()["total"] == 0
    # B's data is unchanged.
    assert (
        client.get(f"/api/v1/returns/{b_data['return']}", headers=b_data["headers"]).json()[
            "status"
        ]
        == "requested"
    )


def _admin_routes():
    for path, operations in app.openapi()["paths"].items():
        if path.startswith("/api/v1/admin"):
            for method in operations:
                yield method.upper(), re.sub(r"\{[^}]+\}", "1", path)


ADMIN_ROUTES = sorted(set(_admin_routes()))


def test_every_admin_route_is_covered():
    assert len(ADMIN_ROUTES) >= 30


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_customers_get_403_on_every_admin_route(client, customer, method, path):
    response = client.request(method, path, headers=customer, json={})
    assert response.status_code == 403, (method, path, response.status_code)
    assert error_code(response) == "admin_required"


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_visitors_get_401_on_every_admin_route(client, method, path):
    response = client.request(method, path, json={})
    assert response.status_code == 401, (method, path)
