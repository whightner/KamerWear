"""Support conversations: ownership, links, validation, polling, read state, admin."""

import pytest
from sqlalchemy import select

from app.models import SupportMessage
from tests.after_sales import new_order, order_items
from tests.commerce import signup
from tests.test_auth import error_code

API = "/api/v1/support/conversations"
ADMIN = "/api/v1/admin/support/conversations"


def start(client, headers, message="Hello, does the hoodie run small?", subject="sizing", **extra):
    return client.post(API, json={"subject": subject, "message": message, **extra}, headers=headers)


def send(client, headers, number, body, admin=False):
    base = ADMIN if admin else API
    return client.post(f"{base}/{number}/messages", json={"body": body}, headers=headers)


@pytest.fixture
def conversation(client, customer) -> str:
    response = start(client, customer)
    assert response.status_code == 201, response.text
    return response.json()["conversation_number"]


def test_create_and_read_own_conversation(client, customer, conversation):
    body = client.get(f"{API}/{conversation}", headers=customer).json()
    assert body["conversation_number"].startswith("KS-")
    assert body["subject"] == "sizing" and body["subject_label"] == "Sizing question"
    assert body["status"] == "open" and body["order_number"] is None
    assert [m["sender_role"] for m in body["messages"]] == ["customer"]
    assert body["messages"][0]["sender_name"] == "Alex"
    listing = client.get(API, headers=customer).json()
    assert listing["total"] == 1
    assert listing["items"][0]["last_message_preview"].startswith("Hello")


def test_support_requires_login(client):
    assert client.get(API).status_code == 401
    assert client.post(API, json={}).status_code == 401


def test_other_customers_cannot_read_or_write(client, customer, conversation):
    other = signup(client, "sam@example.com")
    for response in (
        client.get(f"{API}/{conversation}", headers=other),
        client.get(f"{API}/{conversation}/messages", headers=other),
        send(client, other, conversation, "hi"),
        client.post(f"{API}/{conversation}/close", headers=other),
    ):
        assert response.status_code == 404
        assert error_code(response) == "conversation_not_found"
    assert client.get(API, headers=other).json()["total"] == 0


def test_link_to_own_order_and_return(client, db_session, customer, delivered_order):
    linked = start(client, customer, subject="order_issue", order_number=delivered_order.lower())
    assert linked.status_code == 201 and linked.json()["order_number"] == delivered_order
    item = order_items(db_session, delivered_order)["CHT-RED-L"]
    ret = client.post(
        "/api/v1/returns",
        json={
            "order_number": delivered_order,
            "items": [{"order_item_id": item, "quantity": 1, "reason": "damaged"}],
        },
        headers=customer,
    ).json()["return_number"]
    about_return = start(client, customer, subject="return_question", return_number=ret).json()
    assert about_return["return_number"] == ret
    assert about_return["order_number"] == delivered_order  # filled from the return


def test_cannot_link_someone_elses_order_or_return(client, db_session, customer, delivered_order):
    other = signup(client, "sam@example.com")
    response = start(client, other, order_number=delivered_order)
    assert response.status_code == 404 and error_code(response) == "order_not_found"
    response = start(client, other, return_number="KR-2026-AAAAAA")
    assert response.status_code == 404 and error_code(response) == "return_not_found"


def test_mismatched_order_and_return_links(client, db_session, customer, admin, delivered_order):
    second = new_order(client, db_session, customer, lines=(("CHT-BLACK-M", 1),))
    item = order_items(db_session, delivered_order)["CHT-RED-L"]
    ret = client.post(
        "/api/v1/returns",
        json={
            "order_number": delivered_order,
            "items": [{"order_item_id": item, "quantity": 1, "reason": "damaged"}],
        },
        headers=customer,
    ).json()["return_number"]
    response = start(client, customer, order_number=second, return_number=ret)
    assert response.status_code == 422 and error_code(response) == "conversation_link_mismatch"


@pytest.mark.parametrize(
    ("body", "code"),
    [("", "message_empty"), ("   \n ", "message_empty"), ("x" * 2001, "message_too_long")],
)
def test_message_validation(client, customer, conversation, body, code):
    response = send(client, customer, conversation, body)
    assert response.status_code == 422 and error_code(response) == code
    response = start(client, customer, message=body)
    assert response.status_code == 422 and error_code(response) == code


def test_giant_payload_is_refused(client, customer, conversation):
    response = send(client, customer, conversation, "x" * 50_000)
    assert response.status_code == 422


def test_max_length_message_is_accepted(client, customer, conversation):
    assert send(client, customer, conversation, "x" * 2000).status_code == 201


def test_html_is_stored_and_returned_as_plain_text(client, db_session, customer, conversation):
    payload = '<script>alert("x")</script><img src=x onerror=alert(1)> & done'
    response = send(client, customer, conversation, payload)
    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["body"] == payload  # unchanged text, escaped by the UI
    stored = db_session.scalar(select(SupportMessage).order_by(SupportMessage.id.desc()))
    assert stored.body == payload


def test_customer_cannot_post_as_store(client, customer, conversation):
    response = client.post(
        f"{API}/{conversation}/messages",
        json={"body": "I am the store", "sender_role": "store"},
        headers=customer,
    )
    assert response.status_code == 422
    send(client, customer, conversation, "plain")
    roles = {
        m["sender_role"]
        for m in client.get(f"{API}/{conversation}", headers=customer).json()["messages"]
    }
    assert roles == {"customer"}


def test_close_and_reopen(client, customer, conversation):
    closed = client.post(f"{API}/{conversation}/close", headers=customer).json()
    assert closed["status"] == "closed" and closed["closed_at"] is not None
    response = send(client, customer, conversation, "Anyone?")
    assert response.status_code == 409 and error_code(response) == "conversation_closed"
    reopened = client.post(f"{API}/{conversation}/reopen", headers=customer).json()
    assert reopened["status"] == "open" and reopened["closed_at"] is None
    assert send(client, customer, conversation, "Back again").status_code == 201


def test_admin_list_read_reply_and_customer_polls(client, admin, customer, conversation):
    counts = client.get("/api/v1/admin/attention", headers=admin).json()
    assert counts["conversations_unread"] == 1
    listing = client.get(ADMIN, headers=admin).json()
    assert listing["items"][0]["customer"]["email"] == "alex@example.com"
    assert listing["items"][0]["unread_count"] == 1
    assert client.get(ADMIN, params={"unread_only": True}, headers=admin).json()["total"] == 1

    detail = client.get(f"{ADMIN}/{conversation}", headers=admin).json()
    assert detail["unread_count"] == 0  # opening marks customer messages read
    assert client.get("/api/v1/admin/attention", headers=admin).json()["conversations_unread"] == 0
    last_seen = detail["last_message_id"]

    reply = send(client, admin, conversation, "It runs true to size.", admin=True)
    assert reply.status_code == 201
    assert reply.json()["sender_role"] == "store"
    assert reply.json()["sender_name"] == "KamerWear support"

    assert client.get("/api/v1/support/unread-count", headers=customer).json()["unread"] == 1
    polled = client.get(
        f"{API}/{conversation}/messages", params={"after_id": last_seen}, headers=customer
    ).json()
    assert [m["body"] for m in polled["messages"]] == ["It runs true to size."]
    assert polled["last_message_id"] == reply.json()["id"]
    assert client.get("/api/v1/support/unread-count", headers=customer).json()["unread"] == 0
    # Nothing new: an empty answer that keeps the cursor.
    empty = client.get(
        f"{API}/{conversation}/messages",
        params={"after_id": polled["last_message_id"]},
        headers=customer,
    ).json()
    assert empty["messages"] == [] and empty["last_message_id"] == polled["last_message_id"]


def test_admin_filters_close_and_closed_reply(client, admin, customer, delivered_order):
    first = start(client, customer).json()["conversation_number"]
    linked = start(client, customer, subject="order_issue", order_number=delivered_order).json()

    def numbers(**params):
        body = client.get(ADMIN, params=params, headers=admin).json()
        return [c["conversation_number"] for c in body["items"]]

    assert numbers(q=delivered_order) == [linked["conversation_number"]]
    assert set(numbers(q="Alex")) == {first, linked["conversation_number"]}
    client.post(f"{ADMIN}/{first}/close", headers=admin)
    assert numbers(status="closed") == [first]
    assert numbers(status="open") == [linked["conversation_number"]]
    response = send(client, admin, first, "Late reply", admin=True)
    assert response.status_code == 409 and error_code(response) == "conversation_closed"
    detail = client.get(f"{ADMIN}/{linked['conversation_number']}", headers=admin).json()
    assert detail["order"]["order_number"] == delivered_order and detail["return_request"] is None


def test_customer_cannot_use_admin_support(client, customer, conversation):
    for response in (
        client.get(ADMIN, headers=customer),
        client.get(f"{ADMIN}/{conversation}", headers=customer),
        send(client, customer, conversation, "as store?", admin=True),
        client.post(f"{ADMIN}/{conversation}/close", headers=customer),
        client.get("/api/v1/admin/attention", headers=customer),
    ):
        assert response.status_code == 403 and error_code(response) == "admin_required"


def test_messages_are_rate_limited(client, customer, conversation):
    codes = [send(client, customer, conversation, f"m{i}").status_code for i in range(31)]
    assert codes[:29] == [201] * 29  # 1 conversation start + 29 messages = 30
    assert codes[-1] == 429
