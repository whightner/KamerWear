"""Returns: eligibility, quantities, value, state machine, restocking, refunds, access."""

import threading
import uuid

import pytest
from sqlalchemy import select

from app.models import Inventory, ProductVariant, ReturnStatusHistory
from tests.after_sales import advance, age_delivery, new_order, order_items
from tests.commerce import signup
from tests.test_admin_store import stock
from tests.test_auth import error_code

ADMIN = "/api/v1/admin/returns"


def eligibility(client, headers, number):
    return client.get(f"/api/v1/orders/{number}/return-eligibility", headers=headers)


def request_return(client, headers, number, items, **extra):
    return client.post(
        "/api/v1/returns", json={"order_number": number, "items": items, **extra}, headers=headers
    )


def line(item_id, quantity=1, reason="wrong_size", **extra):
    return {"order_item_id": item_id, "quantity": quantity, "reason": reason, **extra}


def act(client, admin, number, action, **body):
    return client.post(f"{ADMIN}/{number}/{action}", json=body, headers=admin)


@pytest.fixture
def requested(client, db_session, customer, delivered_order) -> str:
    """A requested return of 1 x CHT-BLACK-M (wrong size) and 1 x CHT-RED-L (damaged)."""
    ids = order_items(db_session, delivered_order)
    response = request_return(
        client,
        customer,
        delivered_order,
        [line(ids["CHT-BLACK-M"]), line(ids["CHT-RED-L"], reason="damaged", note="Torn seam")],
        customer_note="Please call before pickup",
    )
    assert response.status_code == 201, response.text
    return response.json()["return_number"]


# --- Eligibility ----------------------------------------------------------------------


def test_delivered_order_is_eligible_with_window_from_delivery(client, customer, delivered_order):
    body = eligibility(client, customer, delivered_order).json()
    assert body["eligible"] is True and body["window_days"] == 7
    assert body["delivered_at"] is not None and body["return_deadline"] > body["delivered_at"]
    quantities = {i["sku"]: i["returnable_quantity"] for i in body["items"]}
    assert quantities == {"CHT-BLACK-M": 2, "CHT-RED-L": 1}


def test_order_not_delivered_cannot_be_returned(client, db_session, customer, admin):
    number = new_order(client, db_session, customer)
    advance(client, admin, number, until="out_for_delivery")
    body = eligibility(client, customer, number).json()
    assert body["eligible"] is False and body["code"] == "return_not_eligible"
    assert all(i["returnable_quantity"] == 0 for i in body["items"])
    ids = order_items(db_session, number)
    response = request_return(client, customer, number, [line(ids["CHT-BLACK-M"])])
    assert response.status_code == 409 and error_code(response) == "return_not_eligible"


def test_window_counts_from_delivery_not_order_date(client, db_session, customer, delivered_order):
    age_delivery(db_session, delivered_order, 6)
    assert eligibility(client, customer, delivered_order).json()["eligible"] is True
    age_delivery(db_session, delivered_order, 2)  # now 8 days ago
    body = eligibility(client, customer, delivered_order).json()
    assert body["code"] == "return_window_expired"
    ids = order_items(db_session, delivered_order)
    response = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"])])
    assert response.status_code == 409 and error_code(response) == "return_window_expired"


def test_quantity_limit_and_previous_returns(client, db_session, customer, delivered_order):
    ids = order_items(db_session, delivered_order)
    too_many = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 3)])
    assert too_many.status_code == 422 and error_code(too_many) == "return_quantity_exceeded"
    assert too_many.json()["detail"]["max_quantity"] == 2

    first = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 1)])
    assert first.status_code == 201
    again = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 2)])
    assert again.status_code == 422 and again.json()["detail"]["max_quantity"] == 1
    assert (
        request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 1)]).status_code
        == 201
    )
    left = {i["sku"]: i for i in eligibility(client, customer, delivered_order).json()["items"]}
    assert left["CHT-BLACK-M"]["already_returned"] == 2
    assert left["CHT-BLACK-M"]["returnable_quantity"] == 0


def test_cancelled_and_rejected_returns_free_the_quantity(
    client, db_session, customer, admin, delivered_order
):
    ids = order_items(db_session, delivered_order)
    first = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 2)])
    client.post(f"/api/v1/returns/{first.json()['return_number']}/cancel", headers=customer)
    second = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 2)])
    assert second.status_code == 201
    act(client, admin, second.json()["return_number"], "reject", note="Worn item")
    assert (
        request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 2)]).status_code
        == 201
    )


@pytest.mark.parametrize(
    "items",
    [
        [line(999_999)],  # not in this order
        [{"order_item_id": 1, "quantity": 0, "reason": "other"}],
        [{"order_item_id": 1, "quantity": 1, "reason": "too_expensive"}],
    ],
)
def test_invalid_items_are_refused(client, customer, delivered_order, items):
    response = request_return(client, customer, delivered_order, items)
    assert response.status_code == 422


def test_duplicate_lines_are_refused(client, db_session, customer, delivered_order):
    item = order_items(db_session, delivered_order)["CHT-BLACK-M"]
    response = request_return(client, customer, delivered_order, [line(item), line(item)])
    assert response.status_code == 422 and error_code(response) == "return_item_invalid"


@pytest.mark.parametrize("field", ["user_id", "return_value", "refund_total", "price"])
def test_client_cannot_send_owner_or_money(client, db_session, customer, delivered_order, field):
    item = order_items(db_session, delivered_order)["CHT-BLACK-M"]
    response = request_return(client, customer, delivered_order, [line(item)], **{field: 1})
    assert response.status_code == 422


def test_value_uses_purchase_time_prices(client, db_session, customer, delivered_order):
    ids = order_items(db_session, delivered_order)
    # The catalog price changes after the purchase: the return keeps the old one.
    db_session.scalar(
        select(ProductVariant).where(ProductVariant.sku == "CHT-BLACK-M")
    ).price_override = 1
    db_session.flush()
    body = request_return(client, customer, delivered_order, [line(ids["CHT-BLACK-M"], 2)]).json()
    unit = body["items"][0]["unit_price"]
    assert unit > 1 and body["return_value"] == unit * 2 == body["items"][0]["line_value"]


# --- Customer views ------------------------------------------------------------------


def test_create_list_and_detail(client, customer, delivered_order, requested):
    detail = client.get(f"/api/v1/returns/{requested}", headers=customer).json()
    assert detail["status"] == "requested" and detail["order_number"] == delivered_order
    assert detail["return_number"].startswith("KR-")
    assert detail["reason_summary"] == "Wrong size, Item damaged"
    assert detail["item_count"] == 2 and detail["can_cancel"] is True
    assert detail["customer_note"] == "Please call before pickup"
    assert [e["status"] for e in detail["history"]] == ["requested"]
    listing = client.get("/api/v1/returns", headers=customer).json()
    assert listing["total"] == 1 and listing["items"][0]["return_number"] == requested
    refs = client.get(f"/api/v1/orders/{delivered_order}/return-eligibility", headers=customer)
    assert refs.json()["returns"][0]["return_number"] == requested


def test_customer_cancels_only_while_requested(client, admin, customer, requested):
    cancelled = client.post(f"/api/v1/returns/{requested}/cancel", headers=customer)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["resolved_at"] is not None
    again = client.post(f"/api/v1/returns/{requested}/cancel", headers=customer)
    assert again.status_code == 409 and error_code(again) == "invalid_return_transition"


def test_cannot_cancel_after_approval(client, admin, customer, requested):
    act(client, admin, requested, "approve")
    response = client.post(f"/api/v1/returns/{requested}/cancel", headers=customer)
    assert response.status_code == 409


def test_other_customers_cannot_see_or_cancel(client, customer, delivered_order, requested):
    other = signup(client, "sam@example.com")
    for response in (
        client.get(f"/api/v1/returns/{requested}", headers=other),
        client.post(f"/api/v1/returns/{requested}/cancel", headers=other),
        client.get(f"/api/v1/orders/{delivered_order}/return-eligibility", headers=other),
    ):
        assert response.status_code == 404
    assert client.get("/api/v1/returns", headers=other).json()["total"] == 0
    assert request_return(client, other, delivered_order, [line(1)]).status_code == 404


def test_returns_require_login(client):
    assert client.get("/api/v1/returns").status_code == 401
    assert client.post("/api/v1/returns", json={}).status_code == 401


# --- Admin processing ----------------------------------------------------------------


def test_customers_cannot_use_admin_return_endpoints(client, customer, requested):
    for response in (
        client.get(ADMIN, headers=customer),
        client.get(f"{ADMIN}/{requested}", headers=customer),
        act(client, customer, requested, "approve"),
        act(client, customer, requested, "reject"),
    ):
        assert response.status_code == 403 and error_code(response) == "admin_required"
    assert (
        client.get(f"/api/v1/returns/{requested}", headers=customer).json()["status"] == "requested"
    )


def test_full_lifecycle_with_restock_refund_and_history(
    client, db_session, admin, customer, requested
):
    before_black, before_red = stock(db_session, "CHT-BLACK-M"), stock(db_session, "CHT-RED-L")
    approved = act(client, admin, requested, "approve", note="Send it back", internal_note="OK")
    assert approved.status_code == 200 and approved.json()["allowed_actions"] == ["receive"]
    assert stock(db_session, "CHT-BLACK-M") == before_black  # approval: no stock change

    items = {i["sku"]: i["id"] for i in approved.json()["items"]}
    received = act(
        client,
        admin,
        requested,
        "receive",
        items=[
            {"return_item_id": items["CHT-BLACK-M"], "restock": True},
            {"return_item_id": items["CHT-RED-L"], "restock": False},  # damaged
        ],
    )
    assert received.status_code == 200, received.text
    on_hand, reserved = stock(db_session, "CHT-BLACK-M")
    assert (on_hand, reserved) == (before_black[0] + 1, before_black[1])
    assert stock(db_session, "CHT-RED-L") == before_red  # not restockable

    refunded = act(client, admin, requested, "refund", note="Refunded by Mobile Money (manual)")
    body = refunded.json()
    assert body["status"] == "refunded" and body["refunded_amount"] == body["return_value"]
    assert "No payment-provider refund was executed" in body["refund_note"]
    assert body["allowed_actions"] == []
    assert [e["status"] for e in body["history"]] == [
        "requested",
        "approved",
        "received",
        "refunded",
    ]
    assert body["history"][1]["internal_note"] == "OK"

    customer_view = client.get(f"/api/v1/returns/{requested}", headers=customer).json()
    assert customer_view["status"] == "refunded"
    assert "No payment-provider refund" in customer_view["refund_note"]
    assert "internal_note" not in str(customer_view) and "OK" not in [
        e["note"] for e in customer_view["history"]
    ]
    assert customer_view["history"][1]["note"] == "Send it back"


def test_receive_needs_a_decision_for_every_line(client, db_session, admin, requested):
    approved = act(client, admin, requested, "approve").json()
    first = approved["items"][0]["id"]
    before = stock(db_session, "CHT-BLACK-M")
    response = act(
        client, admin, requested, "receive", items=[{"return_item_id": first, "restock": True}]
    )
    assert response.status_code == 422 and error_code(response) == "restock_decision_required"
    assert stock(db_session, "CHT-BLACK-M") == before
    assert client.get(f"{ADMIN}/{requested}", headers=admin).json()["status"] == "approved"


def test_no_double_restock_on_repeat(client, db_session, admin, requested):
    approved = act(client, admin, requested, "approve").json()
    items = [{"return_item_id": i["id"], "restock": True} for i in approved["items"]]
    before = stock(db_session, "CHT-BLACK-M")
    assert act(client, admin, requested, "receive", items=items).status_code == 200
    repeat = act(client, admin, requested, "receive", items=items)
    assert repeat.status_code == 409 and error_code(repeat) == "invalid_return_transition"
    assert stock(db_session, "CHT-BLACK-M")[0] == before[0] + 1


def test_no_double_refund(client, admin, requested):
    approved = act(client, admin, requested, "approve").json()
    items = [{"return_item_id": i["id"], "restock": False} for i in approved["items"]]
    act(client, admin, requested, "receive", items=items)
    assert act(client, admin, requested, "refund").status_code == 200
    assert act(client, admin, requested, "refund").status_code == 409


@pytest.mark.parametrize(
    ("path", "action"),
    [
        ([], "receive"),
        ([], "refund"),
        (["approve"], "approve"),
        (["approve"], "reject"),
        (["approve"], "refund"),
        (["reject"], "approve"),
        (["reject"], "receive"),
    ],
)
def test_invalid_and_terminal_transitions(client, admin, requested, path, action):
    for step in path:
        assert act(client, admin, requested, step).status_code == 200
    body = {"items": [{"return_item_id": 1, "restock": False}]} if action == "receive" else {}
    response = act(client, admin, requested, action, **body)
    assert response.status_code == 409 and error_code(response) == "invalid_return_transition"


def test_reject_records_customer_reason(client, admin, customer, requested):
    act(client, admin, requested, "reject", note="Item shows signs of wear", internal_note="photo")
    view = client.get(f"/api/v1/returns/{requested}", headers=customer).json()
    assert view["status"] == "rejected" and view["can_cancel"] is False
    assert view["history"][-1]["note"] == "Item shows signs of wear"


def test_full_return_may_mark_order_payment_refunded(client, db_session, admin, customer):
    number = new_order(client, db_session, customer, lines=(("CHT-BLACK-M", 1),))
    advance(client, admin, number)
    client.post(
        f"/api/v1/admin/orders/{number}/payment-status",
        json={"payment_status": "paid"},
        headers=admin,
    )
    ids = order_items(db_session, number)
    created = request_return(client, customer, number, [line(ids["CHT-BLACK-M"])]).json()
    ref = created["return_number"]
    approved = act(client, admin, ref, "approve").json()
    received = act(
        client,
        admin,
        ref,
        "receive",
        items=[{"return_item_id": approved["items"][0]["id"], "restock": True}],
    ).json()
    assert received["can_mark_order_refunded"] is True
    act(client, admin, ref, "refund", mark_order_payment_refunded=True)
    order = client.get(f"/api/v1/admin/orders/{number}", headers=admin).json()
    assert order["payment_status"] == "refunded"


def test_partial_return_cannot_mark_order_payment_refunded(
    client, db_session, admin, customer, delivered_order
):
    client.post(
        f"/api/v1/admin/orders/{delivered_order}/payment-status",
        json={"payment_status": "paid"},
        headers=admin,
    )
    ids = order_items(db_session, delivered_order)
    ref = request_return(client, customer, delivered_order, [line(ids["CHT-RED-L"])]).json()[
        "return_number"
    ]
    approved = act(client, admin, ref, "approve").json()
    act(
        client,
        admin,
        ref,
        "receive",
        items=[{"return_item_id": approved["items"][0]["id"], "restock": False}],
    )
    response = act(client, admin, ref, "refund", mark_order_payment_refunded=True)
    assert response.status_code == 409 and error_code(response) == "order_not_fully_returned"
    assert client.get(f"{ADMIN}/{ref}", headers=admin).json()["status"] == "received"


def test_admin_list_filters(client, admin, customer, delivered_order, requested):
    def numbers(**params):
        body = client.get(ADMIN, params=params, headers=admin).json()
        return [r["return_number"] for r in body["items"]]

    assert numbers() == [requested]
    assert numbers(status="requested") == [requested]
    assert numbers(status="approved") == []
    assert numbers(q=delivered_order) == [requested]
    assert numbers(q="alex@example") == [requested]
    assert numbers(q=requested.lower()) == [requested]
    assert numbers(date_from="2000-01-01", date_to="2999-01-01") == [requested]
    assert numbers(date_from="2999-01-01") == []
    counts = client.get("/api/v1/admin/attention", headers=admin).json()
    assert counts["returns_to_process"] == 1


def test_history_records_actors(client, db_session, admin, customer, requested):
    act(client, admin, requested, "approve")
    rows = db_session.scalars(select(ReturnStatusHistory).order_by(ReturnStatusHistory.id)).all()
    assert len({row.actor_user_id for row in rows}) == 2  # customer, then admin


def test_concurrent_receive_restocks_once(db_engine):
    """Two staff marking the same return received at once: stock goes up once."""
    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.models import (
        Address,
        Cart,
        CartItem,
        Order,
        OrderStatus,
        PaymentMethod,
        ReturnRequest,
        User,
    )
    from app.schemas.orders import OrderCreate
    from app.services import orders
    from app.services import returns as service
    from app.services.errors import ServiceError

    sku = "CHT-RED-L"
    with Session(db_engine) as db:
        inv = db.scalar(select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku))
        original = (inv.on_hand, inv.reserved)
        inv.on_hand, inv.reserved = 5, 0
        user = User(email=f"ret-{uuid.uuid4().hex[:8]}@kamerwear.cm", password_hash="x")
        db.add(user)
        db.flush()
        address = Address(
            user_id=user.id,
            label="Home",
            recipient_name="R",
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
                Cart(user_id=user.id, items=[CartItem(variant_id=inv.variant_id, quantity=1)]),
            ]
        )
        db.flush()
        order, _ = orders.create_order(
            db,
            user,
            OrderCreate(address_id=address.id, payment_method=PaymentMethod.card),
            "k-" + uuid.uuid4().hex,
        )
        for status in ("confirmed", "preparing", "shipped", "out_for_delivery", "delivered"):
            orders.change_status(db, order, OrderStatus(status))
        request = service.create_return(
            db,
            user,
            order.order_number,
            [service.NewItem(order.items[0].id, 1, service.ReturnReason.wrong_size, None)],
            None,
        )
        service.approve(db, request, user)
        number, user_id, item_id = request.return_number, user.id, request.items[0].id
        db.commit()
        after_delivery = db.scalar(
            select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku)
        ).on_hand

    barrier = threading.Barrier(2)
    results = []

    def receive():
        with Session(db_engine) as db:
            target = db.scalar(select(ReturnRequest).where(ReturnRequest.return_number == number))
            staff = db.get(User, user_id)
            target.items  # load before waiting
            barrier.wait()
            try:
                service.receive(db, target, staff, {item_id: True})
                db.commit()
                results.append("ok")
            except ServiceError as exc:
                db.rollback()
                results.append(exc.code)

    try:
        threads = [threading.Thread(target=receive) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert sorted(results) == ["invalid_return_transition", "ok"], results
        with Session(db_engine) as db:
            inv = db.scalar(
                select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku)
            )
            assert inv.on_hand == after_delivery + 1
    finally:
        with Session(db_engine) as db:
            db.execute(delete(Order).where(Order.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            inv = db.scalar(
                select(Inventory).join(Inventory.variant).where(ProductVariant.sku == sku)
            )
            inv.on_hand, inv.reserved = original
            db.commit()
