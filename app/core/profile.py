from __future__ import annotations

from app.core.config import settings

COMPANY_PROFILE = "company"
DEMO_PROFILE = "demo"


def is_company_profile() -> bool:
    """Return True when the installation is running in the locked-down company profile."""
    return settings.app_profile == COMPANY_PROFILE


def is_demo_profile() -> bool:
    """Return True for the flexible demo/portfolio profile."""
    return settings.app_profile == DEMO_PROFILE
