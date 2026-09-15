"""Tasks repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.clock import to_utc_iso, utc_now


def create_task(
    conn: sqlite3.Connection,
    user_id: int,
    title: str,
    description: str | None = None,
    due_at: str | None = None,
    status: str = "open",
) -> dict[str, Any]:
    """Insert a task and return the row."""
    created_at = to_utc_iso(utc_now())
    cur = conn.execute(
        """
        INSERT INTO tasks (
            user_id, title, description, status, due_at,
            created_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL)
        """,
        (user_id, title, description, status, due_at, created_at),
    )
    conn.commit()
    return get_task(conn, cur.lastrowid)  # type: ignore[arg-type]


def get_task(
    conn: sqlite3.Connection,
    task_id: int,
) -> dict[str, Any] | None:
    """Fetch task by id."""
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    return dict(row) if row else None


def list_tasks(
    conn: sqlite3.Connection,
    *,
    user_id: int | None = None,
    status: str | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List tasks with optional filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if due_from is not None:
        clauses.append("due_at >= ?")
        params.append(due_from)
    if due_to is not None:
        clauses.append("due_at <= ?")
        params.append(due_to)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(int(limit), 200))
    sql = (
        f"SELECT * FROM tasks {where} "
        f"ORDER BY created_at DESC LIMIT ?"
    )
    params.append(safe_limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def complete_task(
    conn: sqlite3.Connection,
    task_id: int,
) -> dict[str, Any] | None:
    """Mark task as completed."""
    completed_at = to_utc_iso(utc_now())
    conn.execute(
        """
        UPDATE tasks
        SET status = 'completed', completed_at = ?
        WHERE id = ?
        """,
        (completed_at, task_id),
    )
    conn.commit()
    return get_task(conn, task_id)
