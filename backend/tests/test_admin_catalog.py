"""Admin categories, products, variants and image metadata."""

import pytest

from tests.test_auth import error_code

API = "/api/v1/admin"
PRODUCT = {
    "name": "Kribi Linen Shirt",
    "slug": "kribi-linen-shirt",
    "category_id": 2,
    "description": "Light linen for the coast.",
    "gender": "men",
    "product_type": "Shirt",
    "base_price": 18500,
    "compare_at_price": 22000,
    "search_keywords": "linen summer",
}


def create_product(client, admin, **changes):
    response = client.post(f"{API}/products", json={**PRODUCT, **changes}, headers=admin)
    assert response.status_code == 201, response.text
    return response.json()


def add_variant(client, admin, product_id, **changes):
    body = {
        "sku": "KLS-WHITE-M",
        "size": "M",
        "color_name": "White",
        "color_hex": "#f5f5f0",
        "on_hand": 8,
        **changes,
    }
    return client.post(f"{API}/products/{product_id}/variants", json=body, headers=admin)


def shop_slugs(client):
    return {p["slug"] for p in client.get("/api/v1/products?limit=100").json()["items"]}


# Categories


def test_list_categories_with_counts(client, admin):
    categories = client.get(f"{API}/categories", headers=admin).json()
    clothing = next(c for c in categories if c["slug"] == "clothing")
    assert clothing["product_count"] >= 1 and clothing["active_product_count"] >= 1


def test_create_and_edit_category(client, admin):
    created = client.post(
        f"{API}/categories",
        json={"name": " Bags ", "slug": "Bags", "description": ""},
        headers=admin,
    )
    assert created.status_code == 201
    body = created.json()
    assert (body["name"], body["slug"], body["description"], body["product_count"]) == (
        "Bags",
        "bags",
        None,
        0,
    )
    edited = client.patch(
        f"{API}/categories/{body['id']}",
        json={"description": "Totes and backpacks"},
        headers=admin,
    )
    assert edited.json()["description"] == "Totes and backpacks"


@pytest.mark.parametrize(
    "body", [{"name": "", "slug": "x"}, {"name": "X", "slug": "Not a slug!"}, {"name": "X"}]
)
def test_invalid_category_rejected(client, admin, body):
    assert client.post(f"{API}/categories", json=body, headers=admin).status_code == 422


def test_category_slug_unique(client, admin):
    response = client.post(
        f"{API}/categories", json={"name": "Shoes 2", "slug": "shoes"}, headers=admin
    )
    assert response.status_code == 409 and error_code(response) == "slug_already_exists"
    other = client.post(f"{API}/categories", json={"name": "Bags", "slug": "bags"}, headers=admin)
    renamed = client.patch(
        f"{API}/categories/{other.json()['id']}", json={"slug": "shoes"}, headers=admin
    )
    assert error_code(renamed) == "slug_already_exists"


def test_deactivate_category_hides_products_and_reactivate_restores(client, admin):
    assert "urban-runner-02" in shop_slugs(client)
    client.patch(f"{API}/categories/1", json={"is_active": False}, headers=admin)  # shoes
    assert "urban-runner-02" not in shop_slugs(client)
    assert client.get("/api/v1/products/urban-runner-02").status_code == 404
    # Still visible to admins, marked as not in the shop.
    product = client.get(f"{API}/products?q=urban runner", headers=admin).json()["items"][0]
    assert product["is_active"] is True and product["visible_in_shop"] is False
    client.patch(f"{API}/categories/1", json={"is_active": True}, headers=admin)
    assert "urban-runner-02" in shop_slugs(client)


def test_unknown_category(client, admin):
    response = client.patch(f"{API}/categories/9999", json={"name": "X"}, headers=admin)
    assert response.status_code == 404 and error_code(response) == "category_not_found"


# Products


def test_create_product_starts_inactive(client, admin):
    product = create_product(client, admin)
    assert product["is_active"] is False and product["visible_in_shop"] is False
    assert product["variants"] == [] and product["images"] == []
    assert product["category"]["slug"] == "clothing"
    assert "kribi-linen-shirt" not in shop_slugs(client)


@pytest.mark.parametrize(
    "changes",
    [
        {"base_price": -1},
        {"base_price": 18500.5},
        {"base_price": "18500"},
        {"base_price": 18500.0},
        {"compare_at_price": 18500},  # not higher than the price
        {"compare_at_price": -5},
        {"gender": "kids"},
        {"name": "  "},
        {"slug": "has spaces"},
        {"rating_average": 5},  # demo review data isn't editable
    ],
)
def test_invalid_product_rejected(client, admin, changes):
    response = client.post(f"{API}/products", json={**PRODUCT, **changes}, headers=admin)
    assert response.status_code == 422, response.text


def test_product_slug_unique_and_category_must_exist(client, admin):
    duplicate = client.post(
        f"{API}/products", json={**PRODUCT, "slug": "classic-hoodie"}, headers=admin
    )
    assert error_code(duplicate) == "slug_already_exists"
    missing = client.post(f"{API}/products", json={**PRODUCT, "category_id": 999}, headers=admin)
    assert error_code(missing) == "category_not_found"


def test_edit_product_and_compare_at_rule_on_update(client, admin):
    product = create_product(client, admin)
    url = f"{API}/products/{product['id']}"
    edited = client.patch(
        url, json={"name": "Kribi Linen Shirt II", "featured": True}, headers=admin
    )
    assert edited.json()["name"] == "Kribi Linen Shirt II" and edited.json()["featured"] is True
    too_high = client.patch(url, json={"base_price": 25000}, headers=admin)  # compare-at is 22000
    assert too_high.status_code == 422 and "compare_at_price" in too_high.json()["detail"]["fields"]
    cleared = client.patch(url, json={"base_price": 25000, "compare_at_price": None}, headers=admin)
    assert cleared.json()["compare_at_price"] is None and cleared.json()["base_price"] == 25000


def test_new_product_full_lifecycle_reaches_the_shop(client, admin):
    product = create_product(client, admin)
    pid = product["id"]
    assert add_variant(client, admin, pid).status_code == 201
    assert (
        add_variant(client, admin, pid, sku="kls-white-l", size="L", on_hand=1).status_code == 201
    )
    client.post(
        f"{API}/products/{pid}/images",
        json={"image_path": "/images/products/classic-hoodie/olive-1.webp", "alt_text": "Shirt"},
        headers=admin,
    )
    client.patch(f"{API}/products/{pid}", json={"is_active": True}, headers=admin)
    assert "kribi-linen-shirt" in shop_slugs(client)
    detail = client.get("/api/v1/products/kribi-linen-shirt").json()
    stock = {v["sku"]: v["available_quantity"] for v in detail["variants"]}
    assert stock == {"KLS-WHITE-M": 8, "KLS-WHITE-L": 1}
    assert detail["sizes"] == ["M", "L"] and detail["price"] == 18500
    assert detail["images"][0]["image_path"].endswith("olive-1.webp")


def test_deactivate_and_reactivate_product(client, admin, db_session):
    url = f"{API}/products/1"
    client.patch(url, json={"is_active": False}, headers=admin)
    assert "urban-runner-02" not in shop_slugs(client)
    assert client.get(f"{API}/products/1", headers=admin).json()["is_active"] is False
    client.patch(url, json={"is_active": True}, headers=admin)
    assert "urban-runner-02" in shop_slugs(client)


def test_admin_product_list_filters_and_stock(client, admin):
    body = client.get(f"{API}/products?limit=100", headers=admin).json()
    assert body["total"] >= 19
    runner = next(p for p in body["items"] if p["slug"] == "urban-runner-02")
    assert runner["variant_count"] > 0 and runner["available_quantity"] > 0
    assert runner["image_path"].startswith("/images/products/")
    shoes = client.get(f"{API}/products?category_id=1", headers=admin).json()
    assert {p["category"]["slug"] for p in shoes["items"]} == {"shoes"}
    client.patch(f"{API}/products/1", json={"is_active": False}, headers=admin)
    inactive = client.get(f"{API}/products?status=inactive", headers=admin).json()
    assert [p["slug"] for p in inactive["items"]] == ["urban-runner-02"]
    low = client.get(f"{API}/products?low_stock=true&limit=100", headers=admin).json()
    assert all(p["low_stock_variant_count"] > 0 for p in low["items"]) and low["total"] > 0
    by_sku = client.get(f"{API}/products?q=UR02-BLACK", headers=admin).json()
    assert [p["slug"] for p in by_sku["items"]] == ["urban-runner-02"]


def test_unknown_product(client, admin):
    response = client.get(f"{API}/products/99999", headers=admin)
    assert response.status_code == 404 and error_code(response) == "product_not_found"


# Variants


def test_variant_create_edit_and_duplicates(client, admin):
    pid = create_product(client, admin)["id"]
    created = add_variant(client, admin, pid).json()
    variant = created["variants"][0]
    assert (variant["sku"], variant["on_hand"], variant["reserved"], variant["price"]) == (
        "KLS-WHITE-M",
        8,
        0,
        18500,
    )
    dup_sku = add_variant(client, admin, pid, sku="UR02-BLACK-43", size="S")
    assert dup_sku.status_code == 409 and error_code(dup_sku) == "sku_already_exists"
    dup_combo = add_variant(client, admin, pid, sku="KLS-OTHER", size="M", color_name="white")
    assert error_code(dup_combo) == "variant_already_exists"
    edited = client.patch(
        f"{API}/variants/{variant['id']}",
        json={"price_override": 19500, "color_hex": "#ffffff"},
        headers=admin,
    ).json()["variants"][0]
    assert edited["price"] == 19500 and edited["color_hex"] == "#ffffff"
    reset = client.patch(
        f"{API}/variants/{variant['id']}", json={"price_override": None}, headers=admin
    )
    assert reset.json()["variants"][0]["price"] == 18500
    taken = client.patch(
        f"{API}/variants/{variant['id']}", json={"sku": "UR02-BLACK-43"}, headers=admin
    )
    assert error_code(taken) == "sku_already_exists"


@pytest.mark.parametrize(
    "changes",
    [
        {"sku": "x"},
        {"sku": "BAD SKU"},
        {"color_hex": "red"},
        {"price_override": -1},
        {"on_hand": -2},
        {"color_name": ""},
    ],
)
def test_invalid_variant_rejected(client, admin, changes):
    pid = create_product(client, admin)["id"]
    assert add_variant(client, admin, pid, **changes).status_code == 422


def test_deactivated_variant_cannot_be_bought(client, admin, db_session, customer):
    from tests.commerce import add_to_cart, variant

    tee = variant(db_session, "CHT-BLACK-M")
    client.patch(f"{API}/variants/{tee.id}", json={"is_active": False}, headers=admin)
    response = add_to_cart(client, customer, tee.id)
    assert response.status_code == 404 and error_code(response) == "variant_not_found"
    shop = client.get("/api/v1/products/core-heavy-tee").json()
    assert "CHT-BLACK-M" not in {v["sku"] for v in shop["variants"]}
    # Still listed for admins.
    detail = client.get(f"{API}/products/{tee.product_id}", headers=admin).json()
    assert next(v for v in detail["variants"] if v["sku"] == "CHT-BLACK-M")["is_active"] is False


# Images


def test_image_add_order_update_remove(client, admin):
    pid = create_product(client, admin)["id"]
    url = f"{API}/products/{pid}/images"
    first = client.post(
        url,
        json={"image_path": "/images/products/kls/white-1.webp", "alt_text": "Front"},
        headers=admin,
    )
    second = client.post(
        url,
        json={
            "image_path": "/images/products/kls/white-2.webp",
            "alt_text": "Back",
            "color_name": "White",
        },
        headers=admin,
    ).json()
    assert [i["position"] for i in second["images"]] == [0, 1]
    back = second["images"][1]
    moved = client.patch(f"{API}/images/{back['id']}", json={"position": 0}, headers=admin).json()
    # Same position: the older image (lower id) comes first, deterministically.
    assert [i["alt_text"] for i in moved["images"]] == ["Front", "Back"]
    front_id = first.json()["images"][0]["id"]
    moved = client.patch(f"{API}/images/{front_id}", json={"position": 5}, headers=admin).json()
    assert [i["alt_text"] for i in moved["images"]] == ["Back", "Front"]
    dup = client.post(
        url,
        json={"image_path": "/images/products/kls/white-1.webp", "alt_text": "x"},
        headers=admin,
    )
    assert error_code(dup) == "image_already_exists"
    removed = client.delete(f"{API}/images/{front_id}", headers=admin).json()
    assert [i["alt_text"] for i in removed["images"]] == ["Back"]
    assert client.delete(f"{API}/images/{front_id}", headers=admin).status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../../secret.webp",
        "/images/products/../../../etc/passwd.webp",
        "/images/products/x/../y.webp",
        "https://evil.example.com/a.webp",
        "/images/products/x/script.js",
        "/images/products/Has Space/a.webp",
        "images/products/x/a.webp",
        "/images/hero/a.webp",
    ],
)
def test_invalid_image_paths_rejected(client, admin, path):
    pid = create_product(client, admin)["id"]
    response = client.post(
        f"{API}/products/{pid}/images", json={"image_path": path, "alt_text": "x"}, headers=admin
    )
    assert response.status_code == 422
    assert "image_path" in response.json()["detail"]["fields"]
