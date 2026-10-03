"""Catalog API tests against PostgreSQL, using the seeded demo catalog."""

from contextlib import contextmanager

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.db.seed import seed_catalog
from app.models import Category, Product, ProductImage, ProductVariant

TOTAL_PRODUCTS = 19


def get_items(client, **params) -> list[dict]:
    response = client.get("/api/v1/products", params={"limit": 100, **params})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(body["items"])
    return body["items"]


def slugs(items: list[dict]) -> list[str]:
    return [item["slug"] for item in items]


@contextmanager
def count_queries(session: Session):
    statements: list[str] = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    engine = session.get_bind().engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


# Categories


def test_lists_active_categories(client):
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert [c["slug"] for c in response.json()] == ["shoes", "clothing", "accessories"]
    assert response.json()[0] == {"id": 1, "name": "Shoes", "slug": "shoes"}


def test_inactive_category_is_hidden(client, db_session):
    db_session.scalar(select(Category).where(Category.slug == "accessories")).is_active = False
    db_session.flush()
    assert "accessories" not in [c["slug"] for c in client.get("/api/v1/categories").json()]
    assert all(i["category"]["slug"] != "accessories" for i in get_items(client))


# Product list


def test_lists_all_products(client):
    items = get_items(client)
    assert len(items) == TOTAL_PRODUCTS
    first = items[0]
    assert first["slug"] == "urban-runner-02"
    assert first["price"] == 28500 and isinstance(first["price"], int)
    assert first["primary_image"]["image_path"].startswith("/images/products/")


def test_pagination(client):
    page1 = client.get("/api/v1/products", params={"limit": 5, "offset": 0}).json()
    page2 = client.get("/api/v1/products", params={"limit": 5, "offset": 5}).json()
    assert page1["total"] == page2["total"] == TOTAL_PRODUCTS
    assert (page1["limit"], page1["offset"], page2["offset"]) == (5, 0, 5)
    assert len(page1["items"]) == len(page2["items"]) == 5
    assert not set(slugs(page1["items"])) & set(slugs(page2["items"]))


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"sort": "random"}, {"gender": "kids"}],
)
def test_rejects_invalid_query_parameters(client, params):
    assert client.get("/api/v1/products", params=params).status_code == 422


def test_category_filter(client):
    items = get_items(client, category="shoes")
    assert slugs(items) == ["urban-runner-02", "flex-knit-runner"]


def test_gender_filter_includes_unisex(client):
    men = get_items(client, gender="men")
    assert {i["gender"] for i in men} == {"men", "unisex"}
    assert len(men) == 13
    assert {i["gender"] for i in get_items(client, gender="unisex")} == {"unisex"}


def test_size_filter(client):
    assert slugs(get_items(client, size="43")) == ["urban-runner-02", "flex-knit-runner"]
    assert all("M" in i["sizes"] for i in get_items(client, size="M"))


def test_price_filter(client):
    items = get_items(client, min_price=10000, max_price=20000)
    assert items and all(10000 <= i["price"] <= 20000 for i in items)


def test_smart_fit_filter(client):
    items = get_items(client, smart_fit="true")
    assert len(items) == 12 and all(i["smart_fit"] for i in items)


def test_on_sale_filter(client):
    items = get_items(client, on_sale="true")
    assert len(items) == 12
    assert all(i["compare_at_price"] > i["price"] and i["discount_percent"] for i in items)


def test_in_stock_filter(client):
    assert "raglan-crew-sweatshirt" not in slugs(get_items(client, in_stock="true"))
    assert slugs(get_items(client, in_stock="false")) == ["raglan-crew-sweatshirt"]


def test_new_filter(client):
    assert all(i["is_new"] for i in get_items(client, is_new="true"))


def test_filters_combine(client):
    items = get_items(client, gender="men", size="M", on_sale="true")
    assert items
    assert all(
        i["gender"] in {"men", "unisex"} and "M" in i["sizes"] and i["discount_percent"]
        for i in items
    )


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("runner", {"urban-runner-02", "flex-knit-runner"}),
        ("hoodie", {"classic-hoodie", "striped-zip-hoodie", "sunset-zip-hoodie"}),
        ("shoes", {"urban-runner-02", "flex-knit-runner"}),
        ("streetwear bomber", {"city-bomber-jacket"}),
        ("lavender", {"classic-hoodie"}),
    ],
)
def test_search(client, q, expected):
    assert set(slugs(get_items(client, q=q))) == expected


def test_search_women_does_not_match_men(client):
    items = get_items(client, q="women")
    assert items and {i["gender"] for i in items} == {"women"}


def test_search_treats_wildcards_literally(client):
    assert get_items(client, q="100%_") == []


@pytest.mark.parametrize(
    ("sort", "key", "reverse"),
    [
        ("price-asc", "price", False),
        ("price-desc", "price", True),
        ("rating", "rating_average", True),
    ],
)
def test_sorting(client, sort, key, reverse):
    values = [i[key] for i in get_items(client, sort=sort)]
    assert values == sorted(values, reverse=reverse)


def test_sort_by_discount(client):
    items = get_items(client, sort="discount")
    discounts = [i["discount_percent"] or 0 for i in items]
    assert discounts == sorted(discounts, reverse=True)
    assert items[0]["slug"] == "core-heavy-tee"


def test_recommended_sort_puts_featured_first(client):
    featured = [i["featured"] for i in get_items(client)]
    assert featured == sorted(featured, reverse=True)


def test_inactive_product_is_hidden(client, db_session):
    db_session.scalar(select(Product).where(Product.slug == "weekend-duffel")).is_active = False
    db_session.flush()
    assert "weekend-duffel" not in slugs(get_items(client))
    assert client.get("/api/v1/products/weekend-duffel").status_code == 404


# Product detail


def test_product_detail(client):
    response = client.get("/api/v1/products/urban-runner-02")
    assert response.status_code == 200
    product = response.json()
    assert product["name"] == "Urban Runner 02"
    assert (product["price"], product["compare_at_price"], product["discount_percent"]) == (
        28500,
        39900,
        29,
    )
    assert product["category"]["slug"] == "shoes"
    assert product["rating_average"] == 4.7 and product["review_count"] == 214
    assert product["smart_fit_demo_size"] == "43"


def test_product_detail_includes_images_in_order(client):
    images = client.get("/api/v1/products/classic-hoodie").json()["images"]
    assert len(images) == 5
    assert [i["position"] for i in images] == sorted(i["position"] for i in images)
    assert {i["color_name"] for i in images} == {"Olive", "Lavender", "Red"}


def test_product_detail_includes_variants_with_inventory(client):
    variants = client.get("/api/v1/products/urban-runner-02").json()["variants"]
    by_size = {v["size"]: v for v in variants}
    assert len(variants) == 6
    assert by_size["45"]["in_stock"] is False and by_size["45"]["available_quantity"] == 0
    assert by_size["43"] == {
        "id": by_size["43"]["id"],
        "sku": "UR02-BLACK-43",
        "size": "43",
        "color_name": "Black",
        "color_hex": "#1b1a19",
        "price": 28500,
        "in_stock": True,
        "available_quantity": 1,
    }


def test_available_quantity_subtracts_reserved_stock(client):
    variants = client.get("/api/v1/products/core-joggers").json()["variants"]
    reserved_variant = next(v for v in variants if v["sku"] == "CJ-BLACK-S")
    assert reserved_variant["available_quantity"] == 5  # 7 on hand - 2 reserved


def test_available_quantity_never_negative(client, db_session):
    variant = db_session.scalar(select(ProductVariant).where(ProductVariant.sku == "WD-NAVY-OS"))
    variant.inventory.reserved = variant.inventory.on_hand + 3
    db_session.flush()
    body = client.get("/api/v1/products/weekend-duffel").json()
    assert body["variants"][0]["available_quantity"] == 0
    assert body["in_stock"] is False


def test_variant_price_override_is_effective_price(client, db_session):
    variant = db_session.scalar(select(ProductVariant).where(ProductVariant.sku == "CHT-BLACK-XXL"))
    variant.price_override = 6500
    db_session.flush()
    variants = client.get("/api/v1/products/core-heavy-tee").json()["variants"]
    prices = {v["sku"]: v["price"] for v in variants}
    assert prices["CHT-BLACK-XXL"] == 6500
    assert prices["CHT-BLACK-M"] == 5500


def test_one_size_product_has_one_variant_per_colour(client):
    product = client.get("/api/v1/products/everyday-backpack").json()
    assert product["sizes"] == []
    assert [(v["size"], v["color_name"]) for v in product["variants"]] == [
        (None, "Grey"),
        (None, "Blue"),
    ]


def test_unknown_product_returns_structured_404(client):
    response = client.get("/api/v1/products/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "product_not_found",
            "message": "No product with slug 'does-not-exist'.",
        }
    }


# Similar products


def test_similar_excludes_current_product_and_matches_type(client):
    items = client.get("/api/v1/products/urban-runner-02/similar").json()
    assert slugs(items) == ["flex-knit-runner"]


def test_similar_for_hoodie_prefers_hoodies_then_related_types(client):
    items = client.get("/api/v1/products/classic-hoodie/similar").json()
    types = [i["product_type"] for i in items]
    assert "classic-hoodie" not in slugs(items)
    assert types[:2] == ["Hoodie", "Hoodie"]
    assert set(types) <= {"Hoodie", "Sweatshirt", "Jacket"}


def test_similar_for_bag_returns_bags(client):
    items = client.get("/api/v1/products/weekend-duffel/similar").json()
    assert items and {i["product_type"] for i in items} == {"Bag"}


def test_similar_for_unknown_product_is_404(client):
    assert client.get("/api/v1/products/nope/similar").status_code == 404


# Seed and performance


def test_seed_is_idempotent(db_session):
    def counts():
        return [
            db_session.scalar(select(func.count()).select_from(model))
            for model in (Category, Product, ProductImage, ProductVariant)
        ]

    before = counts()
    assert before == [3, 19, 69, 189]
    seed_catalog(db_session)
    seed_catalog(db_session)
    assert counts() == before


def test_product_list_uses_constant_number_of_queries(client, db_session):
    with count_queries(db_session) as statements:
        assert len(get_items(client)) == TOTAL_PRODUCTS
    assert len(statements) <= 6, statements


def test_product_detail_uses_constant_number_of_queries(client, db_session):
    with count_queries(db_session) as statements:
        assert client.get("/api/v1/products/classic-hoodie").status_code == 200
    assert len(statements) <= 5, statements
