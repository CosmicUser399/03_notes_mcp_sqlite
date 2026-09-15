"""Domain services for creating notes, tasks, reminders."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.repositories import notes as notes_repo
from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.services.recurrence import dumps_rule


def title_fallback(text: str, max_len: int = 80) -> str:
    """Build title from text when LLM title is empty."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "Без названия"
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def create_note(
    conn: sqlite3.Connection,
    user_id: int,
    text: str,
    title: str | None = None,
) -> dict[str, Any]:
    """Create a note with title fallback."""
    note_title = (title or "").strip() or title_fallback(text)
    return notes_repo.create_note(conn, user_id, note_title, text)


def create_task(
    conn: sqlite3.Connection,
    user_id: int,
    title: str,
    description: str | None = None,
    due_at: str | None = None,
) -> dict[str, Any]:
    """Create an open task."""
    task_title = title.strip() or title_fallback(
        description or "Задача",
    )
    return tasks_repo.create_task(
        conn,
        user_id,
        task_title,
        description=description,
        due_at=due_at,
    )


def create_task_with_reminder(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    title: str,
    description: str | None,
    due_at: str | None,
    remind_at: str,
    recurrence: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create task and linked reminder."""
    task = create_task(
        conn,
        user_id,
        title,
        description=description,
        due_at=due_at,
    )
    rule_raw = dumps_rule(recurrence) if recurrence else None
    reminder = reminders_repo.create_reminder(
        conn,
        task_id=task["id"],
        user_id=user_id,
        remind_at=remind_at,
        recurrence_rule=rule_raw,
    )
    return task, reminder
