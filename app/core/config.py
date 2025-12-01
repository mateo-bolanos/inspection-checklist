from __future__ import annotations

import json
import os
import re
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
        self.app_profile = self._load_app_profile()
        self.jwt_secret = os.getenv("JWT_SECRET", "")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.cors_allow_origins = self._load_cors_origins()
        self.cors_allow_origin_regex = os.getenv(
            "CORS_ALLOW_ORIGIN_REGEX",
            r"http://(localhost|127\.0\.0\.1)(:\d+)?$",
        )
        self.run_migrations_on_startup = self._to_bool(os.getenv("RUN_MIGRATIONS_ON_STARTUP"), default=True)
        self.seed_initial_data = self._to_bool(os.getenv("SEED_INITIAL_DATA"), default=True)
        self.enable_overdue_monitor = self._to_bool(
            os.getenv("ENABLE_OVERDUE_MONITOR"),
            default=self.app_profile == "demo",
        )
        self.enable_scheduler_jobs = self._to_bool(
            os.getenv("ENABLE_SCHEDULER_JOBS"),
            default=self.app_profile == "demo",
        )
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = self._to_bool(os.getenv("SMTP_USE_TLS"), default=True)
        self.smtp_use_ssl = self._to_bool(os.getenv("SMTP_USE_SSL"))
        self.smtp_from_address = os.getenv("SMTP_FROM_ADDRESS") or self.smtp_username
        self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "Safety Inspection Checklist")
        self.supervisor_notification_email = os.getenv("SUPERVISOR_NOTIFICATION_EMAIL")
        self.frontend_base_url = (os.getenv("FRONTEND_BASE_URL") or "http://localhost:5173").rstrip("/")
        self.api_public_base_url = (
            (os.getenv("PUBLIC_API_BASE_URL") or os.getenv("VITE_API_BASE_URL") or "http://localhost:8000")
            .rstrip("/")
        )
        self.inspections_dashboard_path = os.getenv("INSPECTIONS_DASHBOARD_PATH", "/inspections")
        self.inspection_view_path_template = os.getenv(
            "INSPECTION_VIEW_PATH_TEMPLATE",
            "/inspections/{inspection_id}",
        )
        self.inspection_edit_path_template = os.getenv(
            "INSPECTION_EDIT_PATH_TEMPLATE",
            "/inspections/{inspection_id}/edit",
        )
        self._validate_jwt_secret()

    @property
    def database_url(self) -> str:
        """Prefer SQLite for local development unless POSTGRES_URL_ONLY is set."""
        if os.getenv("USE_POSTGRES", "0") in {"1", "true", "True"}:
            return self.postgres_url
        return self.sqlite_url

    def _load_cors_origins(self) -> list[str]:
        raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
        origins: list[str] = []

        if raw:
            origins.extend(self._parse_cors_origins(raw))

        if not origins:
            origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]

        default_frontend_origin = (os.getenv("FRONTEND_BASE_URL") or "http://localhost:5173").rstrip("/")
        if default_frontend_origin:
            origins.append(default_frontend_origin)

        deduped: list[str] = []
        seen: set[str] = set()
        for origin in origins:
            normalized = origin.rstrip("/")
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    @staticmethod
    def _parse_cors_origins(raw: str) -> list[str]:
        """
        Accept comma, whitespace, or JSON-array formatted origin lists.
        """
        if not raw:
            return []

        cleaned = raw.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                loaded = json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(loaded, (list, tuple)):
                    return [
                        str(item).strip().rstrip("/")
                        for item in loaded
                        if isinstance(item, str) and str(item).strip()
                    ]

        tokens = re.split(r"[,\s]+", cleaned)
        return [token.strip().rstrip("/") for token in tokens if token.strip()]

    @staticmethod
    def _to_bool(value: str | None, *, default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in {"1", "true", "yes", "on"}

    def _load_app_profile(self) -> str:
        """
        Determine which deployment profile to run under.
        Defaults to 'company' but accepts 'demo' for the portfolio build.
        """
        profile = (os.getenv("APP_PROFILE") or "company").lower()
        if profile not in {"company", "demo"}:
            profile = "company"
        return profile

    def _validate_jwt_secret(self) -> None:
        """
        Fail fast when JWT_SECRET is unset or trivially weak.
        """
        secret = (self.jwt_secret or "").strip()
        if not secret:
            raise ValueError("JWT_SECRET must be set to a strong, random value")
        if secret.lower() == "change-me":
            raise ValueError("JWT_SECRET cannot use the default placeholder value 'change-me'")
        if len(secret) < 16:
            raise ValueError("JWT_SECRET must be at least 16 characters long")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
