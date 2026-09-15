"""Reminders repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.clock import to_utc_iso, utc_now


def create_reminder(
    conn: sqlite3.Connection,
    *,
    task_id: int,
    user_id: int,
    remind_at: str,
    recurrence_rule: str | None = None,
    status: str = "pending",
) -> dict[str, Any]:
    """Insert a reminder and return the row."""
    created_at = to_utc_iso(utc_now())
    cur = conn.execute(
        """
        INSERT INTO reminders (
            task_id, user_id, remind_at, status,
            recurrence_rule, last_triggered_at, created_at
        ) VALUES (?, ?, ?, ?, ?, NULL, ?)
        """,
        (
            task_id,
            user_id,
            remind_at,
            status,
            recurrence_rule,
            created_at,
        ),
    )
    conn.commit()
    return get_reminder(conn, cur.lastrowid)  # type: ignore[arg-type]


def get_reminder(
    conn: sqlite3.Connection,
    reminder_id: int,
) -> dict[str, Any] | None:
    """Fetch reminder by id."""
    row = conn.execute(
        "SELECT * FROM reminders WHERE id = ?",
        (reminder_id,),
    ).fetchone()
    return dict(row) if row else None


def list_reminders(
    conn: sqlite3.Connection,
    *,
    user_id: int | None = None,
    remind_from: str | None = None,
    remind_to: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List reminders with optional filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if remind_from is not None:
        clauses.append("remind_at >= ?")
        params.append(remind_from)
    if remind_to is not None:
        clauses.append("remind_at <= ?")
        params.append(remind_to)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(int(limit), 200))
    sql = (
        f"SELECT * FROM reminders {where} "
        f"ORDER BY remind_at ASC LIMIT ?"
    )
    params.append(safe_limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def claim_due_reminders(
    conn: sqlite3.Connection,
    now_iso: str,
) -> list[dict[str, Any]]:
    """Select due pending reminders and CAS to processing."""
    due = conn.execute(
        """
        SELECT id FROM reminders
        WHERE status = 'pending' AND remind_at <= ?
        ORDER BY remind_at ASC
        """,
        (now_iso,),
    ).fetchall()
    claimed: list[dict[str, Any]] = []
    for row in due:
        rem_id = row["id"]
        # last_triggered_at marks claim time while processing
        cur = conn.execute(
            """
            UPDATE reminders
            SET status = 'processing', last_triggered_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now_iso, rem_id),
        )
        if cur.rowcount == 1:
            rem = get_reminder(conn, rem_id)
            if rem is not None:
                claimed.append(rem)
    conn.commit()
    return claimed


def mark_sent(
    conn: sqlite3.Connection,
    reminder_id: int,
) -> None:
    """Mark one-shot reminder as sent."""
    now = to_utc_iso(utc_now())
    conn.execute(
        """
        UPDATE reminders
        SET status = 'sent', last_triggered_at = ?
        WHERE id = ?
        """,
        (now, reminder_id),
    )
    conn.commit()


def reschedule_recurring(
    conn: sqlite3.Connection,
    reminder_id: int,
    next_remind_at: str,
) -> None:
    """Set next occurrence for recurring reminder."""
    now = to_utc_iso(utc_now())
    conn.execute(
        """
        UPDATE reminders
        SET status = 'pending',
            remind_at = ?,
            last_triggered_at = ?
        WHERE id = ?
        """,
        (next_remind_at, now, reminder_id),
    )
    conn.commit()


def release_to_pending(
    conn: sqlite3.Connection,
    reminder_id: int,
) -> None:
    """Return processing reminder back to pending."""
    conn.execute(
        """
        UPDATE reminders
        SET status = 'pending'
        WHERE id = ? AND status = 'processing'
        """,
        (reminder_id,),
    )
    conn.commit()


def cancel_reminder(
    conn: sqlite3.Connection,
    reminder_id: int,
) -> None:
    """Cancel reminder so it will not fire."""
    conn.execute(
        """
        UPDATE reminders
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (reminder_id,),
    )
    conn.commit()


def cancel_active_for_task(
    conn: sqlite3.Connection,
    task_id: int,
) -> None:
    """Cancel pending/processing reminders for a task."""
    conn.execute(
        """
        UPDATE reminders
        SET status = 'cancelled'
        WHERE task_id = ?
          AND status IN ('pending', 'processing')
        """,
        (task_id,),
    )
    conn.commit()


def update_remind_at(
    conn: sqlite3.Connection,
    reminder_id: int,
    remind_at: str,
    status: str = "pending",
) -> dict[str, Any] | None:
    """Update next fire time (snooze)."""
    conn.execute(
        """
        UPDATE reminders
        SET remind_at = ?, status = ?
        WHERE id = ?
        """,
        (remind_at, status, reminder_id),
    )
    conn.commit()
    return get_reminder(conn, reminder_id)


def recover_stuck_processing(
    conn: sqlite3.Connection,
    older_than_iso: str,
) -> int:
    """Return stuck processing rows to pending."""
    cur = conn.execute(
        """
        UPDATE reminders
        SET status = 'pending'
        WHERE status = 'processing'
          AND last_triggered_at IS NOT NULL
          AND last_triggered_at < ?
        """,
        (older_than_iso,),
    )
    conn.commit()
    return cur.rowcount
