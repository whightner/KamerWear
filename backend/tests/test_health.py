from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "kamerwear-api"}


def test_root_identifies_api() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "kamerwear-api"
    assert body["health"] == "/api/v1/health"


def test_openapi_docs_are_available() -> None:
    assert client.get("/docs").status_code == 200
    assert "/api/v1/health" in client.get("/openapi.json").json()["paths"]
