"""Notes repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.clock import to_utc_iso, utc_now


def create_note(
    conn: sqlite3.Connection,
    user_id: int,
    title: str,
    text: str,
) -> dict[str, Any]:
    """Insert a note and return the row."""
    now = to_utc_iso(utc_now())
    cur = conn.execute(
        """
        INSERT INTO notes (
            user_id, title, text, created_at, updated_at, archived
        ) VALUES (?, ?, ?, ?, ?, 0)
        """,
        (user_id, title, text, now, now),
    )
    conn.commit()
    return get_note(conn, cur.lastrowid)  # type: ignore[arg-type]


def get_note(
    conn: sqlite3.Connection,
    note_id: int,
) -> dict[str, Any] | None:
    """Fetch note by id."""
    row = conn.execute(
        "SELECT * FROM notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    return dict(row) if row else None


def list_notes(
    conn: sqlite3.Connection,
    *,
    user_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    order: str = "desc",
    limit: int = 20,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    """List notes with optional filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if not include_archived:
        clauses.append("archived = 0")
    if date_from is not None:
        clauses.append("created_at >= ?")
        params.append(date_from)
    if date_to is not None:
        clauses.append("created_at <= ?")
        params.append(date_to)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    direction = "DESC" if order.lower() != "asc" else "ASC"
    safe_limit = max(1, min(int(limit), 200))
    sql = (
        f"SELECT * FROM notes {where} "
        f"ORDER BY created_at {direction} LIMIT ?"
    )
    params.append(safe_limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def search_notes(
    conn: sqlite3.Connection,
    query: str,
    *,
    field: str = "title",
    limit: int = 20,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Search notes by title and/or text (LIKE)."""
    pattern = f"%{query}%"
    clauses: list[str] = ["archived = 0"]
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    field_norm = field.lower()
    if field_norm == "text":
        clauses.append("text LIKE ?")
        params.append(pattern)
    elif field_norm == "both":
        clauses.append("(title LIKE ? OR text LIKE ?)")
        params.extend([pattern, pattern])
    else:
        clauses.append("title LIKE ?")
        params.append(pattern)
    safe_limit = max(1, min(int(limit), 200))
    params.append(safe_limit)
    sql = (
        "SELECT * FROM notes WHERE "
        + " AND ".join(clauses)
        + " ORDER BY created_at DESC LIMIT ?"
    )
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
