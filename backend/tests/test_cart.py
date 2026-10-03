"""Persistent cart: lines, stock limits, ownership and guest-cart merge."""

import pytest

from tests.commerce import add_to_cart, set_stock, signup, variant
from tests.test_auth import error_code


@pytest.fixture
def alex(client):
    return signup(client, "alex@example.com")


def test_empty_cart(client, alex):
    body = client.get("/api/v1/cart", headers=alex).json()
    assert body == {"items": [], "subtotal": 0, "item_count": 0, "has_issues": False}


def test_add_variant_returns_full_line(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")
    body = add_to_cart(client, alex, tee.id, 2).json()
    line = body["items"][0]
    assert line["quantity"] == 2
    assert line["variant"] == {
        "id": tee.id,
        "sku": "CHT-BLACK-M",
        "size": "M",
        "color_name": "Black",
    }
    assert line["product"]["slug"] == "core-heavy-tee"
    assert line["product"]["image"]["image_path"].startswith("/images/products/")
    assert line["unit_price"] == 5500 and line["line_total"] == 11000
    assert line["available_quantity"] == 4 and line["issue"] is None
    assert body["subtotal"] == 11000 and body["item_count"] == 2


def test_same_variant_combines(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")
    add_to_cart(client, alex, tee.id, 1)
    body = add_to_cart(client, alex, tee.id, 2).json()
    assert len(body["items"]) == 1 and body["items"][0]["quantity"] == 3


def test_price_comes_from_catalog_not_client(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")
    response = client.post(
        "/api/v1/cart/items",
        json={"variant_id": tee.id, "quantity": 1, "unit_price": 1},
        headers=alex,
    )
    assert response.status_code == 422  # unknown fields are rejected
    add_to_cart(client, alex, tee.id)
    tee.price_override = 6000
    db_session.flush()
    assert client.get("/api/v1/cart", headers=alex).json()["items"][0]["unit_price"] == 6000


def test_update_and_remove(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")
    item_id = add_to_cart(client, alex, tee.id).json()["items"][0]["cart_item_id"]
    updated = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 4}, headers=alex)
    assert updated.json()["items"][0]["quantity"] == 4
    removed = client.delete(f"/api/v1/cart/items/{item_id}", headers=alex)
    assert removed.json()["items"] == []


def test_clear_cart(client, db_session, alex):
    add_to_cart(client, alex, variant(db_session, "CHT-BLACK-M").id)
    add_to_cart(client, alex, variant(db_session, "CH-RED-M").id)
    assert client.delete("/api/v1/cart", headers=alex).json()["item_count"] == 0


def test_quantity_above_stock_rejected(client, db_session, alex):
    runner = variant(db_session, "UR02-BLACK-43")
    set_stock(db_session, "UR02-BLACK-43", on_hand=1)
    response = add_to_cart(client, alex, runner.id, 5)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "insufficient_stock"
    assert detail["message"] == "Only 1 item remains for Urban Runner 02, EU 43."
    assert detail["items"] == [{"variant_id": runner.id, "available_quantity": 1}]
    # Adding to an existing line counts what's already in the cart.
    assert add_to_cart(client, alex, runner.id, 1).status_code == 200
    assert error_code(add_to_cart(client, alex, runner.id, 1)) == "insufficient_stock"


def test_update_above_stock_rejected_but_lowering_allowed(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")
    item_id = add_to_cart(client, alex, tee.id, 3).json()["items"][0]["cart_item_id"]
    response = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 5}, headers=alex)
    assert error_code(response) == "insufficient_stock"
    set_stock(db_session, "CHT-BLACK-M", on_hand=1)  # stock dropped after adding
    line = client.get("/api/v1/cart", headers=alex).json()["items"][0]
    assert line["issue"] == "Only 1 left. Reduce the quantity to continue."
    lowered = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 1}, headers=alex)
    assert lowered.status_code == 200 and lowered.json()["has_issues"] is False


def test_unavailable_variant_rejected(client, db_session, alex):
    sold_out = variant(db_session, "CHT-BLACK-XXL")
    assert error_code(add_to_cart(client, alex, sold_out.id)) == "insufficient_stock"
    assert add_to_cart(client, alex, 999999).status_code == 404
    inactive = variant(db_session, "CHT-BLACK-M")
    inactive.is_active = False
    db_session.flush()
    assert error_code(add_to_cart(client, alex, inactive.id)) == "variant_not_found"


def test_line_quantity_limit(client, db_session, alex):
    set_stock(db_session, "CHT-BLACK-M", on_hand=50)
    tee = variant(db_session, "CHT-BLACK-M")
    assert add_to_cart(client, alex, tee.id, 11).status_code == 422
    add_to_cart(client, alex, tee.id, 10)
    assert error_code(add_to_cart(client, alex, tee.id, 1)) == "quantity_limit"


def test_cart_ownership(client, db_session, alex):
    bella = signup(client, "bella@example.com")
    item_id = add_to_cart(client, alex, variant(db_session, "CHT-BLACK-M").id).json()["items"][0][
        "cart_item_id"
    ]
    assert client.get("/api/v1/cart", headers=bella).json()["items"] == []
    patched = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 2}, headers=bella)
    assert patched.status_code == 404 and error_code(patched) == "cart_item_not_found"
    assert client.delete(f"/api/v1/cart/items/{item_id}", headers=bella).status_code == 404
    assert client.get("/api/v1/cart", headers=alex).json()["items"][0]["quantity"] == 1


def test_cart_requires_authentication(client):
    assert client.get("/api/v1/cart").status_code == 401


def test_merge_combines_caps_and_reports(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")  # 4 available
    runner = variant(db_session, "UR02-BLACK-43")
    sold_out = variant(db_session, "CHT-BLACK-XXL")
    set_stock(db_session, "UR02-BLACK-43", on_hand=1)
    add_to_cart(client, alex, tee.id, 1)  # already in the account cart
    response = client.post(
        "/api/v1/cart/merge",
        json={
            "items": [
                {"variant_id": tee.id, "quantity": 2},
                {"variant_id": tee.id, "quantity": 2},  # duplicate guest lines
                {"variant_id": runner.id, "quantity": 3},
                {"variant_id": sold_out.id, "quantity": 1},
                {"variant_id": 999999, "quantity": 1},
            ]
        },
        headers=alex,
    )
    assert response.status_code == 200
    body = response.json()
    quantities = {line["variant"]["sku"]: line["quantity"] for line in body["cart"]["items"]}
    assert quantities == {"CHT-BLACK-M": 4, "UR02-BLACK-43": 1}
    messages = {a["variant_id"]: a for a in body["adjustments"]}
    assert messages[tee.id]["added"] == 3
    assert messages[runner.id]["message"].startswith("Only 1 available for Urban Runner 02, EU 43")
    assert "sold out" in messages[sold_out.id]["message"]
    assert messages[999999]["added"] == 0


def test_merge_ignores_client_prices(client, db_session, alex):
    tee = variant(db_session, "CHT-BLACK-M")
    response = client.post(
        "/api/v1/cart/merge",
        json={"items": [{"variant_id": tee.id, "quantity": 1, "unit_price": 1}]},
        headers=alex,
    )
    assert response.status_code == 422
