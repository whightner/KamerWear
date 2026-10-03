"""Every admin endpoint requires a signed-in ADMIN, enforced by the API."""

import pytest

from tests.test_auth import error_code

ADMIN_ROUTES = [
    ("GET", "/api/v1/admin/overview", None),
    ("GET", "/api/v1/admin/categories", None),
    ("POST", "/api/v1/admin/categories", {"name": "Bags", "slug": "bags"}),
    ("PATCH", "/api/v1/admin/categories/1", {"is_active": False}),
    ("GET", "/api/v1/admin/products", None),
    ("GET", "/api/v1/admin/products/1", None),
    (
        "POST",
        "/api/v1/admin/products",
        {
            "name": "X",
            "slug": "x",
            "category_id": 1,
            "gender": "men",
            "product_type": "Tee",
            "base_price": 1000,
        },
    ),
    ("PATCH", "/api/v1/admin/products/1", {"is_active": False}),
    (
        "POST",
        "/api/v1/admin/products/1/variants",
        {"sku": "NEW-1", "color_name": "Red", "color_hex": "#ff0000"},
    ),
    ("PATCH", "/api/v1/admin/variants/1", {"is_active": False}),
    (
        "POST",
        "/api/v1/admin/products/1/images",
        {"image_path": "/images/products/x/a.webp", "alt_text": "A"},
    ),
    ("PATCH", "/api/v1/admin/images/1", {"position": 3}),
    ("DELETE", "/api/v1/admin/images/1", None),
    ("GET", "/api/v1/admin/inventory", None),
    ("PATCH", "/api/v1/admin/inventory/1", {"on_hand": 0}),
    ("GET", "/api/v1/admin/orders", None),
    ("GET", "/api/v1/admin/orders/KW-2026-AAAAAA", None),
    ("POST", "/api/v1/admin/orders/KW-2026-AAAAAA/status", {"status": "confirmed"}),
    ("POST", "/api/v1/admin/orders/KW-2026-AAAAAA/payment-status", {"payment_status": "paid"}),
]


def _call(client, method, url, body, headers=None):
    return client.request(method, url, json=body, headers=headers or {})


@pytest.mark.parametrize("method, url, body", ADMIN_ROUTES)
def test_admin_routes_require_login(client, method, url, body):
    response = _call(client, method, url, body)
    assert response.status_code == 401
    assert error_code(response) == "authentication_required"


@pytest.mark.parametrize("method, url, body", ADMIN_ROUTES)
def test_customers_are_forbidden(client, customer, method, url, body):
    response = _call(client, method, url, body, customer)
    assert response.status_code == 403
    assert error_code(response) == "admin_required"


def test_customer_cannot_change_anything(client, db_session, customer):
    """A forbidden request must not have side effects."""
    from app.models import Category, Inventory

    before = db_session.get(Inventory, 1).on_hand
    _call(client, "PATCH", "/api/v1/admin/inventory/1", {"on_hand": 0}, customer)
    _call(client, "PATCH", "/api/v1/admin/categories/1", {"is_active": False}, customer)
    db_session.expire_all()
    assert db_session.get(Inventory, 1).on_hand == before
    assert db_session.get(Category, 1).is_active is True


def test_admin_is_allowed(client, admin):
    assert client.get("/api/v1/admin/overview", headers=admin).status_code == 200
    assert client.get("/api/v1/admin/orders", headers=admin).status_code == 200


def test_public_registration_cannot_create_admin(client):
    from tests.test_auth import register

    assert register(client, email="sneaky@example.com", role="admin").status_code == 422
