"""User repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.clock import to_utc_iso, utc_now


def upsert_user(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    timezone: str,
    default_reminder_time: str,
) -> dict[str, Any]:
    """Insert user or return existing row."""
    existing = get_by_telegram_id(conn, telegram_user_id)
    if existing is not None:
        return existing
    created_at = to_utc_iso(utc_now())
    cur = conn.execute(
        """
        INSERT INTO users (
            telegram_user_id, timezone, default_reminder_time, created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (telegram_user_id, timezone, default_reminder_time, created_at),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def get_by_telegram_id(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> dict[str, Any] | None:
    """Fetch user by Telegram id."""
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_user_id = ?",
        (telegram_user_id,),
    ).fetchone()
    return dict(row) if row else None


def get_by_id(
    conn: sqlite3.Connection,
    user_id: int,
) -> dict[str, Any] | None:
    """Fetch user by primary key."""
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None
