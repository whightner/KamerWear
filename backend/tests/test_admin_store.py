"""Admin inventory, overview, order fulfilment and demo payment states."""

import threading

import pytest
from sqlalchemy import select

from app.models import Inventory, ProductVariant
from tests.commerce import set_stock, signup, variant
from tests.test_auth import error_code

API = "/api/v1/admin"


def stock(db, sku):
    db.expire_all()
    row = db.scalar(select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku))
    return row.on_hand, row.reserved


def move(client, admin, number, status, **extra):
    return client.post(
        f"{API}/orders/{number}/status", json={"status": status, **extra}, headers=admin
    )


# Inventory


def test_inventory_list_and_filters(client, admin, db_session):
    body = client.get(f"{API}/inventory?limit=200", headers=admin).json()
    assert body["low_stock_threshold"] == 5
    row = next(r for r in body["items"] if r["sku"] == "CHT-BLACK-M")
    assert row["available_quantity"] == row["on_hand"] - row["reserved"]
    assert set(row) >= {"product", "size", "color_name", "on_hand", "reserved", "stock_state"}
    low = client.get(f"{API}/inventory?low_stock=true&limit=200", headers=admin).json()["items"]
    assert low and all(0 < r["available_quantity"] <= 5 for r in low)
    out = client.get(f"{API}/inventory?out_of_stock=true&limit=200", headers=admin).json()["items"]
    assert out and all(r["available_quantity"] == 0 and r["stock_state"] == "out" for r in out)
    q = client.get(f"{API}/inventory?q=UR02-BLACK-43", headers=admin).json()["items"]
    assert [r["sku"] for r in q] == ["UR02-BLACK-43"]
    tee = variant(db_session, "CHT-BLACK-M")
    by_product = client.get(f"{API}/inventory?product_id={tee.product_id}&limit=200", headers=admin)
    assert {r["product"]["slug"] for r in by_product.json()["items"]} == {"core-heavy-tee"}


def test_set_on_hand_updates_storefront(client, admin, db_session):
    set_stock(db_session, "CHT-BLACK-M", on_hand=5)
    tee = variant(db_session, "CHT-BLACK-M")
    row = client.patch(f"{API}/inventory/{tee.id}", json={"on_hand": 2}, headers=admin).json()
    assert (row["on_hand"], row["available_quantity"], row["stock_state"]) == (2, 2, "low")
    shop = client.get("/api/v1/products/core-heavy-tee").json()
    assert next(v for v in shop["variants"] if v["sku"] == "CHT-BLACK-M")["available_quantity"] == 2


def test_reserved_is_read_only(client, admin, db_session):
    tee = variant(db_session, "CHT-BLACK-M")
    response = client.patch(
        f"{API}/inventory/{tee.id}", json={"on_hand": 9, "reserved": 0}, headers=admin
    )
    assert response.status_code == 422
    for bad in ({"on_hand": -1}, {"on_hand": 2.5}, {"on_hand": "3"}):
        assert client.patch(f"{API}/inventory/{tee.id}", json=bad, headers=admin).status_code == 422


def test_on_hand_cannot_drop_below_reserved(client, admin, db_session, placed_order):
    on_hand, reserved = stock(db_session, "CHT-BLACK-M")
    assert reserved == 2
    tee = variant(db_session, "CHT-BLACK-M")
    response = client.patch(f"{API}/inventory/{tee.id}", json={"on_hand": 1}, headers=admin)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "inventory_below_reserved"
    assert detail["message"] == (
        "Cannot set on-hand stock to 1 because 2 units are reserved by orders."
    )
    assert stock(db_session, "CHT-BLACK-M") == (on_hand, 2)
    ok = client.patch(f"{API}/inventory/{tee.id}", json={"on_hand": 2}, headers=admin)
    assert ok.status_code == 200 and ok.json()["available_quantity"] == 0


# Overview


def test_overview_metrics(client, admin, db_session, placed_order):
    metrics = client.get(f"{API}/overview", headers=admin).json()["metrics"]
    assert metrics["active_products"] >= 19
    assert metrics["orders_awaiting_action"] == 1
    assert metrics["orders_today"] == 1
    assert metrics["customers"] == 1  # the admin isn't counted
    assert metrics["order_value"] == 2 * 5500 + 1500
    assert metrics["paid_order_value"] == 0
    assert metrics["out_of_stock_variants"] >= 1 and metrics["low_stock_variants"] >= 1
    assert "revenue" not in str(metrics).lower()
    body = client.get(f"{API}/overview", headers=admin).json()
    assert body["recent_orders"][0]["order_number"] == placed_order
    assert all(r["available_quantity"] <= 5 for r in body["low_stock"])


# Orders


def test_admin_sees_all_orders_customers_only_their_own(client, admin, db_session, placed_order):
    from tests.commerce import add_address, add_to_cart, place_order

    bella = signup(client, "bella@example.com")
    address = add_address(client, bella, city="Yaoundé", region="Centre")
    add_to_cart(client, bella, variant(db_session, "CHT-RED-M").id)
    bella_order = place_order(client, bella, address["id"]).json()["order_number"]

    listed = client.get(f"{API}/orders", headers=admin).json()
    assert [o["order_number"] for o in listed["items"]] == [bella_order, placed_order]
    first = listed["items"][1]
    assert first["customer"]["email"] == "alex@example.com" and first["city"] == "Douala"
    assert first["item_count"] == 2
    assert client.get("/api/v1/orders", headers=bella).json()["total"] == 1
    assert client.get(f"/api/v1/orders/{placed_order}", headers=bella).status_code == 404
    assert client.get(f"{API}/orders/{placed_order}", headers=admin).status_code == 200


def test_order_filters(client, admin, placed_order):
    def numbers(query):
        return [
            o["order_number"]
            for o in client.get(f"{API}/orders?{query}", headers=admin).json()["items"]
        ]

    assert numbers("status=pending") == [placed_order]
    assert numbers("status=shipped") == []
    assert numbers("payment_status=pending") == [placed_order]
    assert numbers("city=douala") == [placed_order]
    assert numbers("city=Kribi") == []
    assert numbers(f"q={placed_order[-6:].lower()}") == [placed_order]
    assert numbers("q=alex@example") == [placed_order]
    assert client.get(f"{API}/orders?status=lost", headers=admin).status_code == 422


def test_order_detail_for_admin(client, admin, placed_order):
    detail = client.get(f"{API}/orders/{placed_order}", headers=admin).json()
    assert detail["customer"]["name"] == "Alex Tadji"
    assert detail["items"][0]["sku"] == "CHT-BLACK-M"
    assert detail["delivery"]["landmark"] == "Near Tradex, blue gate"
    assert detail["allowed_statuses"] == ["confirmed", "cancelled"]
    assert detail["allowed_payment_statuses"] == ["paid", "failed"]
    assert detail["status_history"][0]["status"] == "pending"
    missing = client.get(f"{API}/orders/KW-2026-ZZZZZZ", headers=admin)
    assert missing.status_code == 404 and error_code(missing) == "order_not_found"


def test_full_fulfilment_updates_history_tracking_and_inventory(
    client, admin, db_session, customer, placed_order
):
    on_hand, reserved = stock(db_session, "CHT-BLACK-M")
    for status in ("confirmed", "preparing", "shipped", "out_for_delivery"):
        response = move(client, admin, placed_order, status, note=f"Now {status}")
        assert response.status_code == 200, response.text
        tracking = client.get(f"/api/v1/orders/{placed_order}", headers=customer).json()
        assert tracking["status"] == status
        current = next(s for s in tracking["timeline"] if s["state"] == "current")
        assert current["status"] == status
        assert stock(db_session, "CHT-BLACK-M") == (on_hand, reserved)  # still reserved
    delivered = move(client, admin, placed_order, "delivered", internal_note="Signed by Alex")
    assert delivered.json()["allowed_statuses"] == []
    assert stock(db_session, "CHT-BLACK-M") == (on_hand - 2, reserved - 2)
    history = delivered.json()["status_history"]
    assert [e["status"] for e in history] == [
        "pending",
        "confirmed",
        "preparing",
        "shipped",
        "out_for_delivery",
        "delivered",
    ]
    assert history[-1]["changed_by"] == "staff@kamerwear.cm"
    customer_view = client.get(f"/api/v1/orders/{placed_order}", headers=customer).json()
    assert all(step["state"] == "done" for step in customer_view["timeline"])
    assert customer_view["status_history"][1]["note"] == "Now confirmed"
    # Internal notes never reach the customer.
    assert "Signed by Alex" not in str(customer_view)
    assert "internal_note" not in customer_view["status_history"][-1]
    # Delivering again can't take stock twice.
    again = move(client, admin, placed_order, "delivered")
    assert again.status_code == 409 and error_code(again) == "invalid_order_transition"
    assert stock(db_session, "CHT-BLACK-M") == (on_hand - 2, reserved - 2)


@pytest.mark.parametrize(
    "path, target",
    [
        ([], "shipped"),
        ([], "delivered"),
        (["confirmed"], "pending"),
        (["confirmed", "preparing", "shipped"], "cancelled"),
        (["confirmed", "preparing", "shipped", "out_for_delivery", "delivered"], "preparing"),
        (["cancelled"], "confirmed"),
    ],
)
def test_invalid_transitions_rejected(client, admin, placed_order, path, target):
    for status in path:
        assert move(client, admin, placed_order, status).status_code == 200
    response = move(client, admin, placed_order, target)
    assert response.status_code == 409
    assert error_code(response) == "invalid_order_transition"


def test_cancellation_releases_stock_once(client, admin, db_session, customer, placed_order):
    on_hand, reserved = stock(db_session, "CHT-BLACK-M")
    move(client, admin, placed_order, "confirmed")
    cancelled = move(client, admin, placed_order, "cancelled", note="Cancelled at your request.")
    assert cancelled.status_code == 200
    assert stock(db_session, "CHT-BLACK-M") == (on_hand, reserved - 2)
    again = move(client, admin, placed_order, "cancelled")
    assert again.status_code == 409
    assert stock(db_session, "CHT-BLACK-M") == (on_hand, reserved - 2)
    view = client.get(f"/api/v1/orders/{placed_order}", headers=customer).json()
    assert view["status"] == "cancelled" and view["is_cancelled"] is True
    assert client.get("/api/v1/orders", headers=customer).json()["total"] == 1


# Payments (demo / manual)


def pay(client, admin, number, status, **extra):
    return client.post(
        f"{API}/orders/{number}/payment-status",
        json={"payment_status": status, **extra},
        headers=admin,
    )


def test_payment_transitions(client, admin, customer, placed_order):
    assert error_code(pay(client, admin, placed_order, "refunded")) == "invalid_payment_transition"
    failed = pay(client, admin, placed_order, "failed", note="MoMo declined (demo)")
    assert failed.json()["payment_status"] == "failed"
    assert pay(client, admin, placed_order, "pending").status_code == 200  # retry
    paid = pay(client, admin, placed_order, "paid", note="Cash received (manual)").json()
    assert paid["allowed_payment_statuses"] == ["refunded"]
    assert [(e["from_status"], e["to_status"]) for e in paid["payment_history"]] == [
        ("pending", "failed"),
        ("failed", "pending"),
        ("pending", "paid"),
    ]
    assert paid["payment_history"][-1]["changed_by"] == "staff@kamerwear.cm"
    assert error_code(pay(client, admin, placed_order, "failed")) == "invalid_payment_transition"
    assert pay(client, admin, placed_order, "refunded").json()["allowed_payment_statuses"] == []
    assert (
        client.get(f"/api/v1/orders/{placed_order}", headers=customer).json()["payment_status"]
        == "refunded"
    )


def test_cancelled_order_can_only_be_refunded(client, admin, placed_order):
    move(client, admin, placed_order, "cancelled")
    assert error_code(pay(client, admin, placed_order, "paid")) == "invalid_payment_transition"


def test_concurrent_cancellations_release_stock_once(db_engine):
    """Two admins cancelling the same order at once: one succeeds, stock moves once."""
    import uuid

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.models import Address, Cart, CartItem, OrderStatus, PaymentMethod, User
    from app.schemas.orders import OrderCreate
    from app.services import orders
    from app.services.errors import ServiceError

    with Session(db_engine) as db:
        inv = db.scalar(
            select(Inventory).join(Inventory.variant).where(ProductVariant.sku == "CHT-RED-L")
        )
        original = (inv.on_hand, inv.reserved)
        inv.on_hand, inv.reserved = 5, 0
        user = User(email=f"cancel-{uuid.uuid4().hex[:8]}@kamerwear.cm", password_hash="x")
        db.add(user)
        db.flush()
        address = Address(
            user_id=user.id,
            label="Home",
            recipient_name="C",
            phone="+237699000000",
            region="Littoral",
            city="Douala",
            quarter="Akwa",
            street_or_landmark="Near a",
            is_default=True,
        )
        db.add_all(
            [
                address,
                Cart(user_id=user.id, items=[CartItem(variant_id=inv.variant_id, quantity=2)]),
            ]
        )
        db.flush()
        order, _ = orders.create_order(
            db,
            user,
            OrderCreate(address_id=address.id, payment_method=PaymentMethod.card),
            "k-" + uuid.uuid4().hex,
        )
        number, user_id = order.order_number, user.id
        db.commit()

    barrier = threading.Barrier(2)
    results = []

    def cancel():
        with Session(db_engine) as db:
            from app.models import Order

            target = db.scalar(select(Order).where(Order.order_number == number))
            barrier.wait()
            try:
                orders.change_status(db, target, OrderStatus.cancelled)
                db.commit()
                results.append("ok")
            except ServiceError as exc:
                db.rollback()
                results.append(exc.code)

    try:
        threads = [threading.Thread(target=cancel) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert sorted(results) == ["invalid_order_transition", "ok"], results
        with Session(db_engine) as db:
            inv = db.scalar(
                select(Inventory).join(Inventory.variant).where(ProductVariant.sku == "CHT-RED-L")
            )
            assert (inv.on_hand, inv.reserved) == (5, 0)
    finally:
        with Session(db_engine) as db:
            db.execute(delete(User).where(User.id == user_id))
            inv = db.scalar(
                select(Inventory).join(Inventory.variant).where(ProductVariant.sku == "CHT-RED-L")
            )
            inv.on_hand, inv.reserved = original
            db.commit()
