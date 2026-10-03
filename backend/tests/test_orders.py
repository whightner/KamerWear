"""Checkout quote, order placement, snapshots, history and tracking."""

import re
import uuid

import pytest
from sqlalchemy import select

from app.models import Inventory, Order, OrderStatus, ProductVariant
from app.services.delivery import delivery_fee
from app.services.orders import change_status
from tests.commerce import (
    add_address,
    add_to_cart,
    place_order,
    set_stock,
    signup,
    variant,
)
from tests.test_auth import error_code


@pytest.fixture
def alex(client):
    return signup(client, "alex@example.com")


@pytest.fixture
def ready(client, db_session, alex):
    """Alex with a Douala address and 2 tees + 1 hoodie in the cart."""
    address = add_address(client, alex)
    add_to_cart(client, alex, variant(db_session, "CHT-BLACK-M").id, 2)  # 2 x 5 500
    add_to_cart(client, alex, variant(db_session, "CH-RED-M").id, 1)  # 1 x 14 500
    return address


def quote(client, headers, **body):
    return client.post("/api/v1/checkout/quote", json=body, headers=headers)


def inventory(db, sku) -> Inventory:
    db.expire_all()
    return db.scalar(select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku))


# Delivery fee rule


@pytest.mark.parametrize(
    "city, fee",
    [
        ("Douala", 1500),
        ("  douala ", 1500),
        ("Yaoundé", 2000),
        ("YAOUNDE", 2000),
        ("Bafoussam", 2500),
        ("Kribi", 3500),
    ],
)
def test_delivery_fee_rule(city, fee):
    assert delivery_fee(city) == fee


# Quote


def test_quote_is_server_calculated(client, alex, ready):
    body = quote(client, alex, address_id=ready["id"], payment_method="mobile_money").json()
    assert body["subtotal"] == 25500
    assert body["delivery_fee"] == 1500
    assert body["discount_total"] == 0
    assert body["total"] == 27000
    assert body["item_count"] == 3
    assert body["address"]["city"] == "Douala"
    assert body["payment_note"].startswith("Demo payment — real payment integration is not enabled")
    assert body["issues"] == [] and body["can_place_order"] is True


def test_quote_fee_follows_address_city(client, alex, ready):
    yaounde = add_address(client, alex, city="Yaoundé", region="Centre", quarter="Bastos")
    body = quote(client, alex, address_id=yaounde["id"], payment_method="card").json()
    assert body["delivery_fee"] == 2000 and body["total"] == 27500


def test_quote_rejects_client_totals(client, alex, ready):
    response = quote(client, alex, address_id=ready["id"], delivery_fee=0, total=1)
    assert response.status_code == 422


def test_quote_lists_missing_choices(client, alex, ready):
    body = quote(client, alex).json()
    assert body["delivery_fee"] is None and body["total"] == 25500
    assert body["issues"] == ["Choose a delivery address.", "Choose a payment method."]
    assert body["can_place_order"] is False


def test_quote_empty_cart(client, alex):
    address = add_address(client, alex)
    body = quote(client, alex, address_id=address["id"], payment_method="card").json()
    assert body["issues"][0] == "Your cart is empty." and body["can_place_order"] is False


def test_quote_invalid_or_foreign_address(client, alex, ready):
    bella = signup(client, "bella@example.com")
    foreign = add_address(client, bella)
    for address_id in (foreign["id"], 999999):
        response = quote(client, alex, address_id=address_id, payment_method="card")
        assert response.status_code == 404 and error_code(response) == "address_not_found"


def test_quote_reports_stock_change(client, db_session, alex, ready):
    set_stock(db_session, "CHT-BLACK-M", on_hand=1)
    body = quote(client, alex, address_id=ready["id"], payment_method="card").json()
    assert body["can_place_order"] is False
    assert body["issues"] == ["Core Heavy Tee: Only 1 left. Reduce the quantity to continue."]


# Placing an order


def test_place_order_snapshots_reserves_and_clears_cart(client, db_session, alex, ready):
    before = inventory(db_session, "CHT-BLACK-M")
    on_hand, reserved = before.on_hand, before.reserved

    response = place_order(client, alex, ready["id"], payment_method="mobile_money")
    assert response.status_code == 201, response.text
    order = response.json()
    assert re.fullmatch(r"KW-\d{4}-[2-9A-HJKMNP-Z]{6}", order["order_number"])
    assert order["status"] == "pending" and order["payment_status"] == "pending"
    assert order["payment_method"] == "mobile_money"
    assert (order["subtotal"], order["delivery_fee"], order["total"]) == (
        25500,
        1500,
        27000,
    )
    assert order["item_count"] == 3
    assert order["delivery"] == {
        "label": "Home",
        "recipient_name": "Alex Tadji",
        "phone": "+237699112233",
        "country_code": "CM",
        "region": "Littoral",
        "city": "Douala",
        "quarter": "Bonamoussadi",
        "landmark": "Near Tradex, blue gate",
        "latitude": None,
        "longitude": None,
    }
    tee = next(i for i in order["items"] if i["sku"] == "CHT-BLACK-M")
    assert tee == {
        "product_id": tee["product_id"],
        "variant_id": tee["variant_id"],
        "product_name": "Core Heavy Tee",
        "product_slug": "core-heavy-tee",
        "sku": "CHT-BLACK-M",
        "size": "M",
        "color_name": "Black",
        "image_path": tee["image_path"],
        "unit_price": 5500,
        "quantity": 2,
        "line_total": 11000,
    }
    assert [e["status"] for e in order["status_history"]] == ["pending"]

    after = inventory(db_session, "CHT-BLACK-M")
    assert after.on_hand == on_hand and after.reserved == reserved + 2
    assert client.get("/api/v1/cart", headers=alex).json()["items"] == []


def test_order_keeps_purchase_time_price_and_address(client, db_session, alex, ready):
    number = place_order(client, alex, ready["id"]).json()["order_number"]
    variant(db_session, "CH-RED-M").product.base_price = 18000
    client.patch(f"/api/v1/addresses/{ready['id']}", json={"quarter": "Akwa"}, headers=alex)
    client.delete(f"/api/v1/addresses/{ready['id']}", headers=alex)
    db_session.flush()
    order = client.get(f"/api/v1/orders/{number}", headers=alex).json()
    hoodie = next(i for i in order["items"] if i["sku"] == "CH-RED-M")
    assert hoodie["unit_price"] == 14500
    assert order["delivery"]["quarter"] == "Bonamoussadi"


def test_order_uses_server_price_even_if_changed_since_cart(client, db_session, alex, ready):
    variant(db_session, "CHT-BLACK-M").price_override = 6000
    db_session.flush()
    order = place_order(client, alex, ready["id"]).json()
    assert order["subtotal"] == 2 * 6000 + 14500


def test_expected_total_mismatch_is_rejected(client, db_session, alex, ready):
    response = place_order(client, alex, ready["id"], expected_total=1000)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "quote_changed" and detail["total"] == 27000
    assert client.get("/api/v1/cart", headers=alex).json()["item_count"] == 3
    assert place_order(client, alex, ready["id"], expected_total=27000).status_code == 201


def test_empty_cart_cannot_order(client, alex):
    address = add_address(client, alex)
    response = place_order(client, alex, address["id"])
    assert response.status_code == 400 and error_code(response) == "cart_empty"


def test_invalid_address_cannot_order(client, alex, ready):
    bella = signup(client, "bella@example.com")
    foreign = add_address(client, bella)
    response = place_order(client, alex, foreign["id"])
    assert response.status_code == 404 and error_code(response) == "address_not_found"


def test_stock_changed_after_adding_blocks_order(client, db_session, alex, ready):
    before = inventory(db_session, "CH-RED-M").reserved
    set_stock(db_session, "CHT-BLACK-M", on_hand=3, reserved=2)  # 1 available, 2 in cart
    response = place_order(client, alex, ready["id"])
    assert response.status_code == 409
    assert response.json()["detail"]["message"] == "Only 1 item remains for Core Heavy Tee, M."
    assert inventory(db_session, "CH-RED-M").reserved == before  # nothing reserved
    assert client.get("/api/v1/orders", headers=alex).json()["total"] == 0
    assert client.get("/api/v1/cart", headers=alex).json()["item_count"] == 3


def test_client_cannot_send_prices_or_owner(client, alex, ready):
    response = client.post(
        "/api/v1/orders",
        json={
            "address_id": ready["id"],
            "payment_method": "card",
            "total": 1,
            "user_id": 1,
        },
        headers={**alex, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert response.status_code == 422


def test_idempotency_key_is_required(client, alex, ready):
    response = client.post(
        "/api/v1/orders",
        json={"address_id": ready["id"], "payment_method": "card"},
        headers=alex,
    )
    assert response.status_code == 422


def test_repeated_submit_returns_same_order(client, db_session, alex, ready):
    key = uuid.uuid4().hex
    first = place_order(client, alex, ready["id"], key=key)
    reserved = inventory(db_session, "CHT-BLACK-M").reserved
    second = place_order(client, alex, ready["id"], key=key)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["order_number"] == second.json()["order_number"]
    assert inventory(db_session, "CHT-BLACK-M").reserved == reserved  # not reserved twice
    assert client.get("/api/v1/orders", headers=alex).json()["total"] == 1


def test_order_numbers_are_unique(client, db_session, alex):
    address = add_address(client, alex)
    tee = variant(db_session, "CHT-BLACK-L")
    numbers = set()
    for _ in range(3):
        add_to_cart(client, alex, tee.id)
        numbers.add(place_order(client, alex, address["id"]).json()["order_number"])
    assert len(numbers) == 3
    assert db_session.scalar(select(Order.order_number).where(Order.id > 0).limit(1))


# History and ownership


def test_customer_sees_only_own_orders_newest_first(client, db_session, alex, ready):
    first = place_order(client, alex, ready["id"]).json()["order_number"]
    add_to_cart(client, alex, variant(db_session, "CHT-BLACK-L").id)
    second = place_order(client, alex, ready["id"]).json()["order_number"]

    bella = signup(client, "bella@example.com")
    bella_address = add_address(client, bella)
    add_to_cart(client, bella, variant(db_session, "CHT-RED-M").id)
    place_order(client, bella, bella_address["id"])

    body = client.get("/api/v1/orders", headers=alex).json()
    assert [o["order_number"] for o in body["items"]] == [second, first]
    assert body["total"] == 2
    assert set(body["items"][0]) == {
        "order_number",
        "created_at",
        "status",
        "payment_status",
        "payment_method",
        "total",
        "item_count",
    }


def test_cannot_open_or_track_another_customers_order(client, alex, ready):
    number = place_order(client, alex, ready["id"]).json()["order_number"]
    bella = signup(client, "bella@example.com")
    response = client.get(f"/api/v1/orders/{number}", headers=bella)
    assert response.status_code == 404 and error_code(response) == "order_not_found"
    assert client.get(f"/api/v1/orders/{number}").status_code == 401


def test_order_lookup_is_case_insensitive(client, alex, ready):
    number = place_order(client, alex, ready["id"]).json()["order_number"]
    assert client.get(f"/api/v1/orders/{number.lower()}", headers=alex).status_code == 200


# Tracking


def _states(order):
    return [(step["status"], step["state"]) for step in order["timeline"]]


def test_new_order_timeline(client, alex, ready):
    order = place_order(client, alex, ready["id"]).json()
    assert _states(order) == [
        ("pending", "current"),
        ("confirmed", "upcoming"),
        ("preparing", "upcoming"),
        ("shipped", "upcoming"),
        ("out_for_delivery", "upcoming"),
        ("delivered", "upcoming"),
    ]
    assert order["timeline"][0]["reached_at"] is not None


def test_status_changes_update_timeline_history_and_inventory(client, db_session, alex, ready):
    number = place_order(client, alex, ready["id"]).json()["order_number"]
    stock = inventory(db_session, "CHT-BLACK-M")
    on_hand, reserved = stock.on_hand, stock.reserved
    order = db_session.scalar(select(Order).where(Order.order_number == number))
    for status in (OrderStatus.confirmed, OrderStatus.preparing, OrderStatus.shipped):
        change_status(db_session, order, status, None)
    body = client.get(f"/api/v1/orders/{number}", headers=alex).json()
    assert _states(body)[:4] == [
        ("pending", "done"),
        ("confirmed", "done"),
        ("preparing", "done"),
        ("shipped", "current"),
    ]
    assert [e["status"] for e in body["status_history"]] == [
        "pending",
        "confirmed",
        "preparing",
        "shipped",
    ]
    change_status(db_session, order, OrderStatus.out_for_delivery, None)
    change_status(db_session, order, OrderStatus.delivered, "Handed to Alex")
    stock = inventory(db_session, "CHT-BLACK-M")
    assert (stock.on_hand, stock.reserved) == (on_hand - 2, reserved - 2)
    body = client.get(f"/api/v1/orders/{number}", headers=alex).json()
    assert all(state == "done" for _, state in _states(body))


def test_cancelling_releases_reservation(client, db_session, alex, ready):
    number = place_order(client, alex, ready["id"]).json()["order_number"]
    reserved = inventory(db_session, "CHT-BLACK-M").reserved
    order = db_session.scalar(select(Order).where(Order.order_number == number))
    change_status(db_session, order, OrderStatus.cancelled, "Customer request")
    assert inventory(db_session, "CHT-BLACK-M").reserved == reserved - 2
    body = client.get(f"/api/v1/orders/{number}", headers=alex).json()
    assert body["is_cancelled"] is True
    assert _states(body)[0] == ("pending", "done") and _states(body)[1][1] == "upcoming"
