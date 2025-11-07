from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the application uses an isolated SQLite database for tests
os.environ["SQLITE_URL"] = "sqlite:///./test_app.db"

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
