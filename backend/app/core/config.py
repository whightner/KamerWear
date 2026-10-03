"""Application settings, loaded from environment variables and `backend/.env`."""

from pathlib import Path
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

PROJECT_NAME = "KamerWear API"
SERVICE_NAME = "kamerwear-api"
API_VERSION = "0.1.0"
API_V1_PREFIX = "/api/v1"
JWT_ALGORITHM = "HS256"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Passwordless default for local trust/peer auth; real credentials go in backend/.env.
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/kamerwear"

    # Comma-separated in the environment, e.g. "http://localhost:3000,http://127.0.0.1:3000".
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Authentication. JWT_SECRET_KEY has no default: generate one per environment,
    # e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
    jwt_secret_key: SecretStr | None = None
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    # X-Forwarded-For is only trusted from these hosts (the local Next.js server),
    # so rate limits apply to the real browser IP. Comma-separated.
    trusted_proxy_ips: Annotated[list[str], NoDecode] = ["127.0.0.1", "::1"]

    @field_validator("cors_origins", "trusted_proxy_ips", mode="before")
    @classmethod
    def split_comma_list(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            value = value.split(",")
        return [origin.strip() for origin in value if origin.strip()]

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origin(cls, origins: list[str]) -> list[str]:
        # CORS is configured with credentials enabled, which must never be combined with "*".
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return origins

    @field_validator("jwt_secret_key")
    @classmethod
    def require_strong_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return value
        secret = value.get_secret_value()
        if secret.startswith("CHANGE_ME"):
            raise ValueError("JWT_SECRET_KEY still has the placeholder from .env.example")
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return value

    def jwt_secret(self) -> str:
        """The signing key; authentication cannot work without it."""
        if self.jwt_secret_key is None:
            raise RuntimeError("JWT_SECRET_KEY is not set (see backend/.env.example)")
        return self.jwt_secret_key.get_secret_value()


settings = Settings()
