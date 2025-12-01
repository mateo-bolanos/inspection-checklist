from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure the application uses an isolated SQLite database for tests
os.environ["SQLITE_URL"] = "sqlite:///./test_app.db"
# Ensure deterministic secrets and demo data for tests
os.environ.setdefault("JWT_SECRET", "test-secret-please-change")
os.environ.setdefault("SEED_INITIAL_DATA", "1")
os.environ.setdefault("RUN_MIGRATIONS_ON_STARTUP", "1")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.main import app  # noqa: E402
from app.core.database import engine  # noqa: E402

TEST_DB_PATH = Path("test_app.db")


@pytest.fixture()
def client() -> TestClient:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
