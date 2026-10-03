import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import app


def test_cors_origins_are_read_as_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000")

    assert Settings(_env_file=None).cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_wildcard_cors_origin_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_allows_configured_frontend_origin() -> None:
    origin = settings.cors_origins[0]

    response = TestClient(app).options(
        "/api/v1/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_ignores_unknown_origin() -> None:
    response = TestClient(app).get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
