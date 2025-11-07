from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env values are loaded when the module is imported
load_dotenv(dotenv_path=Path('.') / '.env', override=False)


class Settings:
    """Application configuration sourced from environment variables."""

    def __init__(self) -> None:
        self.sqlite_url = os.getenv("SQLITE_URL", "sqlite:///./app.db")
        self.postgres_url = os.getenv(
            "POSTGRES_URL",
            "postgresql+psycopg://user:password@localhost:5432/inspection",
        )
        self.jwt_secret = os.getenv("JWT_SECRET", "change-me")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    @property
    def database_url(self) -> str:
        """Prefer SQLite for local development unless POSTGRES_URL_ONLY is set."""
        if os.getenv("USE_POSTGRES", "0") in {"1", "true", "True"}:
            return self.postgres_url
        return self.sqlite_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
