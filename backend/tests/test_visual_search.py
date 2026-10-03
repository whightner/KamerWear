"""Visual search: upload validation, index, ranking, type guard, errors, privacy."""

import io
import os
import tempfile

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import func, select, text

from app.ai import encoder as encoder_module
from app.ai.images import catalog_image_path
from app.models import Product, ProductImage, ProductImageEmbedding
from app.services import visual_search
from app.services.visual_search import IndexedImage, _rank
from tests.test_auth import error_code
from tests.visual import GROUP_COLORS, image_bytes

URL = "/api/v1/visual-search"


def search(client, data: bytes, filename="photo.jpg", content_type="image/jpeg", **params):
    return client.post(URL, files={"image": (filename, data, content_type)}, params=params)


def slugs(response) -> list[str]:
    return [item["product"]["slug"] for item in response.json()["items"]]


def product(db, slug) -> Product:
    return db.scalar(select(Product).where(Product.slug == slug))


# --- Upload validation --------------------------------------------------------


@pytest.mark.parametrize(
    "fmt, content_type", [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")]
)
def test_accepts_jpeg_png_webp(client, indexed, fmt, content_type):
    response = search(client, image_bytes(fmt=fmt), f"photo.{fmt.lower()}", content_type)
    assert response.status_code == 200, response.text


def test_rejects_unsupported_format(client, indexed):
    response = search(client, image_bytes(fmt="GIF"), "photo.gif", "image/gif")
    assert response.status_code == 415 and error_code(response) == "unsupported_image_type"
    bmp = search(client, image_bytes(fmt="BMP"), "photo.bmp", "image/bmp")
    assert error_code(bmp) == "unsupported_image_type"


def test_rejects_heic(client, indexed):
    response = search(client, b"\x00\x00\x00\x18ftypheic", "photo.heic", "image/heic")
    assert response.status_code == 415 and error_code(response) == "unsupported_image_type"


def test_rejects_fake_image_with_image_extension(client, indexed):
    response = search(client, b"<?php echo 'not an image'; ?>", "photo.jpg", "image/jpeg")
    assert response.status_code == 400 and error_code(response) == "invalid_image"
    truncated = image_bytes()[:200]
    assert error_code(search(client, truncated)) == "invalid_image"


def test_content_decides_not_the_extension(client, indexed):
    png_named_jpg = search(client, image_bytes(fmt="PNG"), "photo.jpg", "image/jpeg")
    assert png_named_jpg.status_code == 200


def test_rejects_oversized_file(client, indexed):
    response = search(client, b"\xff\xd8" + os.urandom(9 * 1024 * 1024))
    assert response.status_code == 413 and error_code(response) == "image_too_large"


def test_rejects_excessive_dimensions_and_decompression_bombs(client, indexed):
    wide = search(client, image_bytes(size=(9000, 10), fmt="PNG"), "wide.png", "image/png")
    assert wide.status_code == 413 and error_code(wide) == "image_too_large"
    # 49 megapixels of one colour compress to a tiny file: refused before decoding.
    bomb = search(client, image_bytes(size=(7000, 7000), fmt="PNG"), "bomb.png", "image/png")
    assert bomb.status_code == 413 and error_code(bomb) == "image_too_large"


def test_requires_an_image_field(client, indexed):
    response = client.post(URL, data={"note": "no file"})
    assert response.status_code == 400 and error_code(response) == "invalid_image"


def test_limit_is_bounded(client, indexed):
    assert search(client, image_bytes(), limit=25).status_code == 422
    assert len(search(client, image_bytes(), limit=3).json()["items"]) == 3


def test_only_uploads_no_url_fetching(client, indexed):
    response = client.post(URL, data={"image": "https://example.com/shoe.jpg"})
    assert response.status_code == 400 and error_code(response) == "invalid_image"


# --- Index --------------------------------------------------------------------


def test_index_covers_active_images_and_rerun_does_not_duplicate(db_session, fake_encoder, indexed):
    report, _ = indexed
    active = len(visual_search._active_images(db_session))
    assert report.indexed == active and report.failed == 0
    again = visual_search.build_index(db_session, fake_encoder)
    assert (again.indexed, again.unchanged) == (0, active)
    rows = db_session.scalar(select(func.count(ProductImageEmbedding.id)))
    assert rows == active
    forced = visual_search.build_index(db_session, fake_encoder, force=True)
    assert forced.indexed == active
    assert db_session.scalar(select(func.count(ProductImageEmbedding.id))) == active


def test_stored_embeddings_are_normalised(db_session, indexed):
    row = db_session.scalar(select(ProductImageEmbedding).limit(1))
    vector = np.frombuffer(row.embedding, dtype="<f4")
    assert row.dimensions == 4 and abs(float(np.linalg.norm(vector)) - 1) < 1e-5


def test_missing_file_is_reported_not_fatal(db_session, fake_encoder, image_root):
    root, _ = image_root
    image = db_session.scalar(select(ProductImage).order_by(ProductImage.id).limit(1))
    (root / image.image_path.lstrip("/")).unlink()
    report = visual_search.build_index(db_session, fake_encoder)
    assert report.failed == 1 and image.image_path in report.problems[0]
    status = visual_search.index_status(db_session, "loaded")
    assert status.missing_files == [image.image_path]


def test_changed_image_is_stale_until_reindexed(db_session, fake_encoder, indexed, image_root):
    root, _ = image_root
    image = db_session.scalar(select(ProductImage).order_by(ProductImage.id).limit(1))
    Image.new("RGB", (32, 32), (1, 2, 3)).save(root / image.image_path.lstrip("/"), format="WEBP")
    status = visual_search.index_status(db_session, "loaded")
    assert status.stale_images == [image.image_path] and status.ready
    assert visual_search.build_index(db_session, fake_encoder).indexed == 1
    assert visual_search.index_status(db_session, "loaded").stale_images == []


def test_new_admin_image_is_unindexed_until_rebuild(db_session, fake_encoder, indexed, image_root):
    root, _ = image_root
    runner = product(db_session, "urban-runner-02")
    path = "/images/products/urban-runner-02/new-angle.webp"
    Image.new("RGB", (32, 32), GROUP_COLORS["footwear"]).save(
        root / path.lstrip("/"), format="WEBP"
    )
    db_session.add(ProductImage(product_id=runner.id, image_path=path, alt_text="x", position=9))
    db_session.flush()
    assert visual_search.index_status(db_session, "loaded").unindexed_images == [path]
    visual_search.build_index(db_session, fake_encoder)
    assert visual_search.index_status(db_session, "loaded").unindexed_images == []


def test_inactive_products_are_excluded(client, db_session, fake_encoder, indexed):
    runner = product(db_session, "urban-runner-02")
    red = image_bytes(GROUP_COLORS["footwear"])
    assert "urban-runner-02" in slugs(search(client, red))
    runner.is_active = False
    db_session.flush()
    # Excluded at query time immediately, and removed from the index on rebuild.
    assert "urban-runner-02" not in slugs(search(client, red))
    report = visual_search.build_index(db_session, fake_encoder)
    assert report.removed == len(runner.images)


def test_unsafe_image_paths_are_never_read(db_session, fake_encoder, image_root, tmp_path):
    root, _ = image_root
    secret = tmp_path.parent / "secret.webp"
    Image.new("RGB", (8, 8)).save(secret, format="WEBP")
    image = db_session.scalar(select(ProductImage).order_by(ProductImage.id).limit(1))
    image.image_path = "/images/products/../../../secret.webp"
    db_session.flush()
    report = visual_search.build_index(db_session, fake_encoder)
    assert report.failed == 1
    for bad in [
        "/images/products/../../etc/passwd",
        "/etc/passwd",
        "https://evil.example.com/a.webp",
        "/images/hero/a.webp",
        "/images/products//etc/passwd",
    ]:
        with pytest.raises(ValueError):
            catalog_image_path(bad, root)
    assert catalog_image_path("/images/products/a/b.webp", root).is_relative_to(root)


def test_only_one_index_build_at_a_time(db_session, db_engine, fake_encoder, image_root):
    with db_engine.connect() as other:
        other.execute(text("SELECT pg_advisory_lock(:k)"), {"k": visual_search.INDEX_LOCK_KEY})
        try:
            with pytest.raises(visual_search.IndexBusy):
                visual_search.build_index(db_session, fake_encoder)
        finally:
            other.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": visual_search.INDEX_LOCK_KEY}
            )


# --- Similarity and type guard ---------------------------------------------------


def test_closest_product_ranks_first(client, db_session, indexed):
    _, colors = indexed
    hoodie = product(db_session, "classic-hoodie")
    response = search(client, image_bytes(colors[hoodie.id]))
    body = response.json()
    assert body["items"][0]["product"]["slug"] == "classic-hoodie"
    assert body["items"][0]["similarity_score"] > 0.999
    assert body["items"][0]["matched_image"].startswith("/images/products/classic-hoodie/")
    scores = [item["similarity_score"] for item in body["items"] if item["matches_predicted_type"]]
    assert scores == sorted(scores, reverse=True)
    assert "embedding" not in response.text


def test_each_product_appears_once(client, db_session, indexed):
    response = search(client, image_bytes(GROUP_COLORS["outerwear"]), limit=24)
    found = slugs(response)
    assert len(found) == len(set(found))
    hoodie = product(db_session, "classic-hoodie")
    assert len(hoodie.images) > 1  # several gallery images, one result


def test_type_guard_puts_predicted_type_first(client, indexed):
    body = search(client, image_bytes(GROUP_COLORS["footwear"]), limit=24).json()
    assert body["query"]["type_guard_applied"] is True
    assert body["query"]["predicted_type"] == "footwear"
    assert body["query"]["predicted_type_label"] == "Shoes"
    flags = [item["matches_predicted_type"] for item in body["items"]]
    assert flags[:2] == [True, True]  # both sneakers first
    assert all(flags[:2]) and not any(flags[2:])
    assert {i["product"]["category"]["slug"] for i in body["items"][:2]} == {"shoes"}


def test_bag_query_returns_bags_first(client, indexed):
    body = search(client, image_bytes(GROUP_COLORS["bags"]), limit=5).json()
    assert body["query"]["predicted_type"] == "bags"
    assert [i["product"]["category"]["slug"] for i in body["items"][:3]] == ["accessories"] * 3


def test_type_guard_not_applied_when_uncertain(client, indexed):
    body = search(client, image_bytes(GROUP_COLORS["other"])).json()
    assert body["query"]["type_guard_applied"] is False
    assert body["query"]["predicted_type"] is None
    assert all(item["matches_predicted_type"] is None for item in body["items"])
    assert body["items"]  # still returns the closest products


def test_rank_guard_beats_raw_score_only_within_order():
    entries = [
        IndexedImage(1, "/a1", "outerwear"),
        IndexedImage(1, "/a2", "outerwear"),
        IndexedImage(2, "/b1", "footwear"),
        IndexedImage(3, "/c1", "footwear"),
    ]
    scores = np.array([0.95, 0.90, 0.60, 0.70])
    ranked = _rank(entries, scores, limit=10, preferred_group="footwear")
    assert [(pid, path) for pid, _, path, _ in ranked] == [(3, "/c1"), (2, "/b1"), (1, "/a1")]
    plain = _rank(entries, scores, limit=10, preferred_group=None)
    assert [pid for pid, *_ in plain] == [1, 3, 2]


def test_weak_matches_are_flagged(client, indexed, monkeypatch):
    monkeypatch.setattr(visual_search, "WEAK_MATCH_SCORE", 1.5)
    body = search(client, image_bytes()).json()
    assert body["query"]["weak_matches"] is True and body["items"]


# --- Product visual similarity -------------------------------------------------------


def test_visual_similar_excludes_product_and_prefers_same_type(client, indexed):
    body = client.get("/api/v1/products/urban-runner-02/visual-similar?limit=4").json()
    found = [i["product"]["slug"] for i in body["items"]]
    assert "urban-runner-02" not in found
    assert found[0] == "flex-knit-runner" and body["type_guard_applied"] is True
    assert len(found) == 4 and len(set(found)) == 4


def test_visual_similar_errors(client, db_session, fake_encoder, image_root):
    assert client.get("/api/v1/products/nope/visual-similar").status_code == 404
    not_ready = client.get("/api/v1/products/urban-runner-02/visual-similar")
    assert not_ready.status_code == 503 and error_code(not_ready) == "visual_search_not_ready"
    visual_search.build_index(db_session, fake_encoder)
    runner = product(db_session, "urban-runner-02")
    db_session.query(ProductImageEmbedding).filter(
        ProductImageEmbedding.product_image_id.in_([i.id for i in runner.images])
    ).delete(synchronize_session=False)
    missing = client.get("/api/v1/products/urban-runner-02/visual-similar")
    assert missing.status_code == 409 and error_code(missing) == "product_not_indexed"


def test_rule_based_similar_still_exists(client):
    assert client.get("/api/v1/products/urban-runner-02/similar").status_code == 200


# --- Errors: no fake fallback ----------------------------------------------------


def test_model_unavailable_returns_structured_error(client, image_root, monkeypatch):
    encoder_module.set_encoder(None)

    def broken():
        raise encoder_module.EncoderUnavailable("weights missing at /secret/path")

    monkeypatch.setattr("app.api.v1.endpoints.visual_search.get_encoder", broken)
    response = search(client, image_bytes())
    assert response.status_code == 503
    assert error_code(response) == "visual_search_unavailable"
    assert "items" not in response.json() and "/secret/path" not in response.text


def test_model_crash_does_not_leak_internals(client, indexed, fake_encoder, monkeypatch):
    def boom(images):
        raise RuntimeError("CUDA kernel exploded at 0xdeadbeef")

    monkeypatch.setattr(fake_encoder, "encode_images", boom)
    response = search(client, image_bytes())
    assert response.status_code == 503 and "0xdeadbeef" not in response.text


def test_not_ready_without_index(client, fake_encoder, image_root):
    response = search(client, image_bytes())
    assert response.status_code == 503 and error_code(response) == "visual_search_not_ready"


def test_no_searchable_products(client, db_session, indexed):
    db_session.query(Product).update({Product.is_active: False})
    db_session.flush()
    response = search(client, image_bytes())
    assert response.status_code == 404 and error_code(response) == "no_searchable_products"


def test_rate_limited(client, indexed):
    for _ in range(12):
        assert search(client, image_bytes(size=(8, 8))).status_code == 200
    response = search(client, image_bytes(size=(8, 8)))
    assert response.status_code == 429 and error_code(response) == "too_many_searches"


# --- Privacy ----------------------------------------------------------------------


def test_query_image_is_not_retained(client, db_session, indexed):
    before_files = set(os.listdir(tempfile.gettempdir()))
    before_rows = db_session.scalar(select(func.count(ProductImageEmbedding.id)))
    # > 1 MB so the multipart parser spools it to a temporary file.
    noise = Image.fromarray(
        np.random.default_rng(1).integers(0, 255, (900, 900, 3), dtype=np.uint8)
    )
    buffer = io.BytesIO()
    noise.save(buffer, format="PNG")
    assert len(buffer.getvalue()) > 1024 * 1024
    assert search(client, buffer.getvalue(), "big.png", "image/png").status_code == 200
    assert set(os.listdir(tempfile.gettempdir())) - before_files == set()
    assert db_session.scalar(select(func.count(ProductImageEmbedding.id))) == before_rows


def test_exif_is_dropped_and_orientation_applied():
    from app.ai.images import load_upload

    image = Image.new("RGB", (40, 20), (200, 10, 10))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90°
    exif[0x8825] = {2: (4.0, 3.0, 0.0)}  # GPS block
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    loaded = load_upload(buffer.getvalue(), "image/jpeg")
    assert loaded.size == (20, 40)
    assert not loaded.info.get("exif") and len(loaded.getexif()) == 0


# --- Admin ----------------------------------------------------------------------------


def test_admin_status_and_rebuild_are_protected(client, customer):
    for method, path in [("GET", "status"), ("POST", "rebuild")]:
        url = f"/api/v1/admin/visual-search/{path}"
        assert client.request(method, url).status_code == 401
        assert client.request(method, url, headers=customer).status_code == 403


def test_admin_status_and_rebuild(client, admin, db_session, fake_encoder, image_root):
    status = client.get("/api/v1/admin/visual-search/status", headers=admin).json()
    assert status["ready"] is False and status["indexed_images"] == 0
    assert len(status["unindexed_images"]) == status["active_images"] > 0
    rebuilt = client.post("/api/v1/admin/visual-search/rebuild", headers=admin).json()
    assert rebuilt["indexed"] == status["active_images"] and rebuilt["failed"] == 0
    status = client.get("/api/v1/admin/visual-search/status", headers=admin).json()
    assert status["ready"] is True and status["unindexed_images"] == []
    assert status["products_represented"] == status["active_products"]
    assert status["last_run"]["trigger"] == "admin" and status["last_run"]["status"] == "succeeded"
    assert status["model"] == "fake/mean-colour"


def test_admin_rebuild_busy(client, admin, db_engine, fake_encoder, image_root):
    with db_engine.connect() as other:
        other.execute(text("SELECT pg_advisory_lock(:k)"), {"k": visual_search.INDEX_LOCK_KEY})
        try:
            response = client.post("/api/v1/admin/visual-search/rebuild", headers=admin)
            assert response.status_code == 409 and error_code(response) == "index_busy"
        finally:
            other.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": visual_search.INDEX_LOCK_KEY}
            )


def test_admin_rebuild_without_model(client, admin, monkeypatch):
    encoder_module.set_encoder(None)

    def broken():
        raise encoder_module.EncoderUnavailable("no weights")

    monkeypatch.setattr("app.api.v1.endpoints.admin_visual_search.get_encoder", broken)
    response = client.post("/api/v1/admin/visual-search/rebuild", headers=admin)
    assert response.status_code == 503 and error_code(response) == "visual_search_unavailable"
