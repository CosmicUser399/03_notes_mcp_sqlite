"""Database schema initialization."""

from __future__ import annotations

from pathlib import Path

from app.db.connection import get_connection

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_db(db_path: str | None = None) -> None:
    """Create tables and indexes if they do not exist."""
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_connection(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
