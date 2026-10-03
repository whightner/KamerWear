"""Application settings, loaded from environment variables and `backend/.env`."""

from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

PROJECT_NAME = "KamerWear API"
SERVICE_NAME = "kamerwear-api"
API_VERSION = "0.1.0"
API_V1_PREFIX = "/api/v1"


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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
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


settings = Settings()
