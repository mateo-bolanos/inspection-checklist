from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

ONTARIO_TZ = ZoneInfo("America/Toronto")


def build_frontend_url(path_template: str, **kwargs) -> str:
    """Render a frontend-relative path (ensuring a single slash) and prepend the configured base URL."""
    path = path_template.format(**kwargs) if kwargs else path_template
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{settings.frontend_base_url}{normalized}"


def format_date(value: date | None) -> str:
    if not value:
        return "-"
    return value.strftime("%b %d, %Y")


def format_datetime(value: datetime | None) -> str:
    if not value:
        return "-"
    localized = value
    if localized.tzinfo is None:
        localized = localized.replace(tzinfo=timezone.utc)
    localized = localized.astimezone(ONTARIO_TZ)
    return localized.strftime("%b %d, %Y %H:%M %Z")
