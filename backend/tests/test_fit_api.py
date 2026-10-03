"""Smart Fit API: estimates, the confirmed Fit Profile and product recommendations."""

import io
import os
import tempfile

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import func, inspect, select

from app.core.config import settings
from app.fit import pose as pose_module
from app.models import CartItem, FitEstimate, FitProfile, Inventory, Product, ProductVariant
from tests.commerce import signup
from tests.fit import WIDTH, photo_bytes
from tests.test_auth import error_code

FRONT_COLOR, SIDE_COLOR = (200, 60, 60), (60, 200, 60)


def estimate(client, headers, front=None, side=None, height="172", preference="regular"):
    files = {"front": ("front.jpg", front or photo_bytes(FRONT_COLOR), "image/jpeg")}
    if side is not None:
        files["side"] = ("side.jpg", side, "image/jpeg")
    data = {"height_cm": height, "fit_preference": preference}
    return client.post("/api/v1/fit/estimate", files=files, data=data, headers=headers)


def save(client, headers, **body):
    payload = {"height_cm": 172, "fit_preference": "regular", **body}
    return client.put("/api/v1/fit/profile", json=payload, headers=headers)


# --- Access ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/fit/estimate"),
        ("get", "/api/v1/fit/profile"),
        ("put", "/api/v1/fit/profile"),
        ("delete", "/api/v1/fit/profile"),
        ("get", "/api/v1/products/classic-hoodie/fit-recommendation"),
    ],
)
def test_smart_fit_requires_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert error_code(response) == "authentication_required"


def test_size_charts_are_public(client):
    response = client.get("/api/v1/fit/size-charts")
    assert response.status_code == 200
    assert response.json()["version"].startswith("kamerwear-demo-")


# --- Estimates ---------------------------------------------------------------------------


def test_front_only_estimate(client, customer, fake_pose, db_session):
    response = estimate(client, customer)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["used_side_photo"] is False
    assert body["confidence"] == "low"
    assert set(body["measurements"]) == {
        "shoulder_width_cm",
        "chest_cm",
        "waist_cm",
        "hip_cm",
        "inseam_cm",
    }
    assert body["suggested"]["top"] in {"XS", "S", "M", "L", "XL", "XXL"}
    assert set(body["suggested_by_preference"]) == {"slim", "regular", "relaxed"}
    assert body["estimation_version"].endswith("/fake-pose")
    # Not saved as a profile: confirmation is a separate step.
    assert db_session.scalar(select(func.count()).select_from(FitProfile)) == 0
    assert client.get("/api/v1/fit/profile", headers=customer).status_code == 404
    # No pose data or percentages in the response.
    text = response.text.lower()
    assert "landmark" not in text and "accuracy" not in text and "%" not in text


def test_front_and_side_estimate(client, customer, fake_pose):
    response = estimate(client, customer, side=photo_bytes(SIDE_COLOR))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["used_side_photo"] is True
    assert body["confidence"] in {"high", "medium"}
    assert fake_pose.calls == 2


def test_empty_optional_side_field_is_ignored(client, customer, fake_pose):
    files = {
        "front": ("front.jpg", photo_bytes(FRONT_COLOR), "image/jpeg"),
        "side": ("", b"", "application/octet-stream"),
    }
    response = client.post(
        "/api/v1/fit/estimate", files=files, data={"height_cm": "172"}, headers=customer
    )
    assert response.status_code == 200, response.text
    assert response.json()["used_side_photo"] is False


@pytest.mark.parametrize("height", ["99", "231", "abc", ""])
def test_height_must_be_between_100_and_230(client, customer, fake_pose, height):
    response = estimate(client, customer, height=height)
    assert response.status_code == 422
    assert error_code(response) == "invalid_fit_height"
    assert fake_pose.calls == 0


@pytest.mark.parametrize(
    ("data", "content_type", "status", "code"),
    [
        (b"this is not an image", "image/jpeg", 400, "invalid_fit_image"),
        (photo_bytes(fmt="PNG")[:60], "image/png", 400, "invalid_fit_image"),  # malformed
        (photo_bytes(fmt="GIF"), "image/gif", 400, "invalid_fit_image"),
        (b"heic", "image/heic", 400, "invalid_fit_image"),
        (photo_bytes(size=(9000, 40)), "image/jpeg", 413, "fit_image_too_large"),
    ],
)
def test_invalid_photos_are_refused(client, customer, fake_pose, data, content_type, status, code):
    files = {"front": ("front.jpg", data, content_type)}
    response = client.post(
        "/api/v1/fit/estimate", files=files, data={"height_cm": "172"}, headers=customer
    )
    assert response.status_code == status, response.text
    assert error_code(response) == code
    assert response.json()["detail"]["photo"] == "front"
    assert fake_pose.calls == 0


def test_oversized_upload_is_refused_before_parsing(client, customer, fake_pose):
    big = b"\xff\xd8" + b"0" * (17 * 1024 * 1024)
    response = estimate(client, customer, front=big)
    assert response.status_code == 413
    assert error_code(response) == "fit_image_too_large"


def test_decompression_bomb_is_refused(client, customer, fake_pose):
    response = estimate(client, customer, front=photo_bytes(size=(7000, 6000), fmt="PNG"))
    assert response.status_code == 413
    assert error_code(response) == "fit_image_too_large"


@pytest.mark.parametrize(
    ("color", "code"),
    [
        ((60, 60, 200), "fit_pose_not_detected"),
        ((200, 200, 60), "fit_multiple_people"),
        ((200, 60, 200), "fit_full_body_not_visible"),
    ],
)
def test_unusable_pose_explains_the_problem(client, customer, fake_pose, color, code):
    response = estimate(client, customer, front=photo_bytes(color))
    assert response.status_code == 422
    assert error_code(response) == code
    assert response.json()["detail"]["photo"] == "front"


def test_side_photo_problems_name_the_side_photo(client, customer, fake_pose):
    response = estimate(client, customer, side=photo_bytes((120, 120, 120)))
    assert response.status_code == 422
    assert response.json()["detail"]["photo"] == "side"


def test_arms_touching_body_gives_warnings_not_invented_numbers(client, customer, fake_pose):
    response = estimate(client, customer, front=photo_bytes((60, 200, 200)))
    assert response.status_code == 200
    body = response.json()
    assert body["measurements"]["chest_cm"] is None
    assert body["suggested"]["top"] is None
    assert any("arms" in w for w in body["warnings"])


def test_model_unavailable_is_a_clear_error_without_fallback(
    client, customer, monkeypatch, tmp_path, db_session
):
    pose_module.set_backend(None)
    monkeypatch.setattr(settings, "smart_fit_model_path", tmp_path / "missing.task")
    try:
        response = estimate(client, customer)
    finally:
        pose_module.set_backend(None)
    assert response.status_code == 503
    assert error_code(response) == "fit_service_unavailable"
    assert db_session.scalar(select(func.count()).select_from(FitEstimate)) == 0


def test_model_crash_is_reported_as_unavailable(client, customer, fake_pose):
    response = estimate(client, customer, front=photo_bytes((90, 40, 10)))
    assert response.status_code == 503
    assert error_code(response) == "fit_service_unavailable"
    assert "exploded" not in response.text


def test_estimates_are_rate_limited_per_user(client, customer, fake_pose):
    for _ in range(10):
        assert estimate(client, customer).status_code == 200
    response = estimate(client, customer)
    assert response.status_code == 429
    assert error_code(response) == "too_many_fit_estimates"
    other = signup(client, "sam@example.com")
    assert estimate(client, other).status_code == 200


def test_only_the_last_three_estimates_are_kept(client, customer, fake_pose, db_session):
    ids = [estimate(client, customer).json()["estimate_id"] for _ in range(5)]
    kept = db_session.scalars(select(FitEstimate.id).order_by(FitEstimate.id)).all()
    assert kept == ids[-3:]


def test_photos_are_not_stored_anywhere(client, customer, fake_pose, db_session, monkeypatch):
    # No table has a column that could hold an image.
    for table in ("fit_estimates", "fit_profiles"):
        columns = inspect(db_session.connection()).get_columns(table)
        assert all("BYTEA" not in str(c["type"]).upper() for c in columns)
        assert not any(
            "image" in c["name"] or "photo" in c["name"].replace("used_side_photo", "")
            for c in columns
        )
    # Uploads may be spooled to a temporary file; it must be gone afterwards.
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setattr(tempfile, "tempdir", temp_dir)
    noise = np.random.default_rng(1).integers(0, 255, (1600, 1200, 3), dtype=np.uint8)
    noise[:40, :40] = FRONT_COLOR  # the fake backend reads the scenario here
    buffer = io.BytesIO()
    Image.fromarray(noise).save(buffer, format="JPEG", quality=95)
    assert buffer.tell() > 1024 * 1024  # large enough to be spooled to disk
    assert estimate(client, customer, front=buffer.getvalue()).status_code == 200
    assert os.listdir(temp_dir) == []


def test_exif_is_dropped_before_analysis(client, customer, fake_pose):
    image = Image.new("RGB", (WIDTH, 1000), FRONT_COLOR)
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    exif[0x8825] = {1: "N", 2: (4.0, 3.0, 0.0)}  # GPS
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    assert Image.open(io.BytesIO(buffer.getvalue())).getexif()
    response = estimate(client, customer, front=buffer.getvalue())
    assert response.status_code == 200, response.text
    received = fake_pose.received[0]
    assert not received.getexif() and "exif" not in received.info


# --- Fit Profile ---------------------------------------------------------------------


def test_confirming_an_estimate_saves_the_profile(client, customer, fake_pose):
    body = estimate(client, customer, side=photo_bytes(SIDE_COLOR)).json()
    response = save(
        client,
        customer,
        estimate_id=body["estimate_id"],
        top_size=body["suggested"]["top"],
        bottom_size=body["suggested"]["bottom"],
        shoe_size_eu=42,
    )
    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["source"] == "photo_estimate"
    assert profile["confidence"] == body["confidence"]
    assert profile["estimated_measurements"] == body["measurements"]
    assert profile["shoe_size_eu"] == 42
    assert profile["confirmed_by_user"] is True
    assert client.get("/api/v1/fit/profile", headers=customer).json() == profile


def test_customer_corrections_win_over_suggestions(client, customer, fake_pose):
    body = estimate(client, customer).json()
    corrected = "XXL" if body["suggested"]["top"] != "XXL" else "XS"
    response = save(
        client, customer, estimate_id=body["estimate_id"], top_size=corrected, bottom_size="34"
    )
    assert response.status_code == 200
    assert response.json()["top_size"] == corrected
    assert response.json()["source"] == "photo_corrected"
    # A later estimate never changes the confirmed profile by itself.
    estimate(client, customer)
    assert client.get("/api/v1/fit/profile", headers=customer).json()["top_size"] == corrected


def test_client_cannot_send_its_own_measurements(client, customer):
    response = save(client, customer, top_size="M", chest_cm=99)
    assert response.status_code == 422


def test_manual_profile_without_photos(client, customer):
    response = save(client, customer, top_size="M", bottom_size="32", shoe_size_eu=43)
    assert response.status_code == 200
    profile = response.json()
    assert profile["source"] == "manual" and profile["confidence"] is None
    assert profile["bottom_size_letter"] == "M"
    assert all(value is None for value in profile["estimated_measurements"].values())


@pytest.mark.parametrize(
    "body",
    [
        {"top_size": "XXXL"},
        {"bottom_size": "33"},
        {"shoe_size_eu": 60},
        {"height_cm": 90},
        {"height_cm": "172"},
    ],
)
def test_profile_values_are_validated(client, customer, body):
    response = save(client, customer, **body)
    assert response.status_code == 422


def test_changing_height_manually_drops_old_estimated_dimensions(client, customer, fake_pose):
    body = estimate(client, customer).json()
    save(client, customer, estimate_id=body["estimate_id"], top_size="M")
    response = save(client, customer, height_cm=180, top_size="M")
    profile = response.json()
    assert profile["source"] == "manual"
    assert all(value is None for value in profile["estimated_measurements"].values())


def test_estimate_must_match_the_height(client, customer, fake_pose):
    body = estimate(client, customer).json()
    response = save(client, customer, estimate_id=body["estimate_id"], height_cm=180)
    assert response.status_code == 422
    assert error_code(response) == "fit_estimate_mismatch"


def test_another_users_estimate_cannot_be_used(client, customer, fake_pose):
    other = signup(client, "sam@example.com")
    body = estimate(client, other).json()
    response = save(client, customer, estimate_id=body["estimate_id"], top_size="M")
    assert response.status_code == 404
    assert error_code(response) == "fit_estimate_not_found"


def test_profiles_are_private_to_each_customer(client, customer):
    save(client, customer, top_size="L")
    other = signup(client, "sam@example.com")
    assert client.get("/api/v1/fit/profile", headers=other).status_code == 404
    save(client, other, top_size="S")
    assert client.get("/api/v1/fit/profile", headers=customer).json()["top_size"] == "L"
    client.delete("/api/v1/fit/profile", headers=other)
    assert client.get("/api/v1/fit/profile", headers=customer).status_code == 200


def test_rescan_and_confirm_replaces_the_profile(client, customer, fake_pose):
    first = estimate(client, customer).json()
    save(client, customer, estimate_id=first["estimate_id"], top_size="S")
    second = estimate(client, customer, side=photo_bytes(SIDE_COLOR)).json()
    response = save(
        client, customer, estimate_id=second["estimate_id"], top_size=second["suggested"]["top"]
    )
    assert response.json()["confidence"] == second["confidence"]
    assert response.json()["top_size"] == second["suggested"]["top"]


def test_delete_removes_profile_and_estimates_but_not_the_account(
    client, customer, fake_pose, db_session
):
    body = estimate(client, customer).json()
    save(client, customer, estimate_id=body["estimate_id"], top_size="M")
    response = client.delete("/api/v1/fit/profile", headers=customer)
    assert response.status_code == 204
    assert client.get("/api/v1/fit/profile", headers=customer).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(FitEstimate)) == 0
    assert client.get("/api/v1/users/me", headers=customer).status_code == 200


# --- Product recommendations ------------------------------------------------------------


def recommendation(client, headers, slug):
    response = client.get(f"/api/v1/products/{slug}/fit-recommendation", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def set_size_stock(db, slug: str, size: str, on_hand: int) -> None:
    rows = db.scalars(
        select(Inventory)
        .join(Inventory.variant)
        .join(ProductVariant.product)
        .where(Product.slug == slug, ProductVariant.size == size)
    ).all()
    assert rows
    for row in rows:
        row.on_hand, row.reserved = on_hand, 0
    db.flush()


def test_no_profile_and_unsupported_products(client, customer):
    assert recommendation(client, customer, "classic-hoodie")["status"] == "no_profile"
    assert recommendation(client, customer, "canvas-messenger-bag")["status"] == "unsupported"
    # Not marked for Smart Fit in the catalog.
    assert recommendation(client, customer, "raglan-crew-sweatshirt")["status"] == "unsupported"


def test_top_recommendation_uses_the_confirmed_size(client, customer):
    save(client, customer, top_size="M")
    result = recommendation(client, customer, "classic-hoodie")
    assert result["status"] == "recommended"
    assert (result["kind"], result["size"], result["size_label"]) == ("top", "M", "M")


def test_trousers_use_numeric_or_letter_sizes_like_the_product(client, customer):
    save(client, customer, bottom_size="32")
    numeric = recommendation(client, customer, "everyday-cargo")
    assert (numeric["status"], numeric["size"]) == ("recommended", "32")
    letters = recommendation(client, customer, "core-joggers")
    assert (letters["status"], letters["size"]) == ("recommended", "M")


def test_shoes_use_the_confirmed_shoe_size_only(client, customer):
    save(client, customer, top_size="M")
    missing = recommendation(client, customer, "urban-runner-02")
    assert missing["status"] == "missing_size" and missing["size"] is None
    save(client, customer, top_size="M", shoe_size_eu=43)
    shoe = recommendation(client, customer, "urban-runner-02")
    assert (shoe["status"], shoe["size_label"]) == ("recommended", "EU 43")


def test_unavailable_size_is_explained_with_the_nearest_size(client, customer, db_session):
    save(client, customer, top_size="M")
    set_size_stock(db_session, "classic-hoodie", "M", 0)
    result = recommendation(client, customer, "classic-hoodie")
    assert result["status"] == "unavailable"
    assert result["size"] == "M"
    assert result["nearest_available"] == "L"
    assert "Your usual size is M, but M is unavailable" in result["message"]


def test_size_not_made_for_this_product(client, customer):
    save(client, customer, top_size="XXL")  # classic hoodie: S-XL
    result = recommendation(client, customer, "classic-hoodie")
    assert result["status"] == "not_offered"
    assert result["nearest_available"] == "XL"


def test_recommendation_never_touches_the_cart(client, customer, db_session):
    save(client, customer, top_size="M")
    recommendation(client, customer, "classic-hoodie")
    assert db_session.scalar(select(func.count()).select_from(CartItem)) == 0


def test_recommendation_disappears_after_deleting_the_profile(client, customer):
    save(client, customer, top_size="M")
    client.delete("/api/v1/fit/profile", headers=customer)
    assert recommendation(client, customer, "classic-hoodie")["status"] == "no_profile"
