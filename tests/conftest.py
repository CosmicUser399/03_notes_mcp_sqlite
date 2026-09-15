"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DEFAULT_TIMEZONE", "Europe/Berlin")
os.environ.setdefault("DEFAULT_REMINDER_TIME", "09:00")


@pytest.fixture
def db_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Isolated SQLite file and settings override."""
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("SQLITE_PATH", path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.config import get_settings
    from app.db.migrate import init_db

    get_settings.cache_clear()
    init_db(path)
    yield path
    get_settings.cache_clear()


@pytest.fixture
def conn(db_path: str):
    """Open connection to temp DB."""
    from app.db.connection import get_connection

    connection = get_connection(db_path)
    yield connection
    connection.close()
