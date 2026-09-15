"""SQLite connection helpers with WAL mode."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import get_settings


def _ensure_parent_dir(db_path: str) -> None:
    parent = Path(db_path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open SQLite connection with WAL and foreign keys."""
    path = db_path or get_settings().sqlite_path
    _ensure_parent_dir(path)
    conn = sqlite3.connect(path, timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
