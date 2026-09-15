"""Unified chronological feed for /list_N."""

from __future__ import annotations

import sqlite3
from typing import Any


def list_feed(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return latest notes, tasks, reminders for a user."""
    safe_limit = max(1, min(int(limit), 50))
    sql = """
        SELECT * FROM (
            SELECT
                'note' AS entity_type,
                id AS entity_id,
                title AS title,
                text AS body,
                created_at AS created_at
            FROM notes
            WHERE user_id = ? AND archived = 0

            UNION ALL

            SELECT
                'task' AS entity_type,
                id AS entity_id,
                title AS title,
                COALESCE(description, '') AS body,
                created_at AS created_at
            FROM tasks
            WHERE user_id = ?

            UNION ALL

            SELECT
                'reminder' AS entity_type,
                r.id AS entity_id,
                COALESCE(t.title, 'reminder') AS title,
                r.remind_at AS body,
                r.created_at AS created_at
            FROM reminders r
            LEFT JOIN tasks t ON t.id = r.task_id
            WHERE r.user_id = ?
        )
        ORDER BY created_at DESC
        LIMIT ?
    """
    rows = conn.execute(
        sql,
        (user_id, user_id, user_id, safe_limit),
    ).fetchall()
    return [dict(r) for r in rows]
