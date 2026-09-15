"""Shared helpers for Telegram handlers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.db.connection import get_connection
from app.db.repositories import users as users_repo
from app.services import entities
from app.services.clock import (
    local_to_utc,
    to_utc_iso,
    tomorrow_at_default,
    utc_now,
)
from app.services.intent import IntentName, IntentResult, parse_intent
from app.telegram import texts

logger = logging.getLogger(__name__)


def ensure_user(
    settings: Settings,
    telegram_user_id: int,
) -> dict[str, Any]:
    """Upsert and return user row."""
    conn = get_connection()
    try:
        return users_repo.upsert_user(
            conn,
            telegram_user_id,
            settings.default_timezone,
            settings.default_reminder_time,
        )
    finally:
        conn.close()


def _as_utc_iso(
    value: datetime | None,
    tz_name: str,
) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return to_utc_iso(local_to_utc(value, tz_name))
    return to_utc_iso(value.astimezone(timezone.utc))


def apply_intent(
    settings: Settings,
    user: dict[str, Any],
    text: str,
    forced_intent: IntentName | None = None,
) -> str:
    """Parse intent, persist entities, return reply text."""
    try:
        result = parse_intent(
            settings,
            text,
            timezone=user["timezone"],
            default_reminder_time=user["default_reminder_time"],
            utc_now_iso=to_utc_iso(utc_now()),
            forced_intent=forced_intent,
        )
    except Exception:
        logger.exception("intent parse failed")
        return texts.PARSE_ERROR

    return persist_intent(user, result)


def persist_intent(
    user: dict[str, Any],
    result: IntentResult,
) -> str:
    """Write IntentResult to SQLite and build confirmation."""
    tz_name = user["timezone"]
    intent = result.intent
    if intent in ("query", "unknown"):
        return texts.UNKNOWN_INTENT

    due_iso = _as_utc_iso(result.due_at, tz_name)
    remind_iso = _as_utc_iso(result.remind_at, tz_name)

    if intent == "reminder" and remind_iso is None:
        remind_iso = to_utc_iso(
            tomorrow_at_default(
                tz_name,
                user["default_reminder_time"],
            )
        )

    if intent == "reminder" and remind_iso is None:
        return texts.BAD_DATE

    conn = get_connection()
    try:
        if intent == "note":
            note = entities.create_note(
                conn,
                user["id"],
                result.text or result.title,
                title=result.title or None,
            )
            return texts.note_created(note)

        title = result.title or result.text or "Задача"
        description = result.text or None
        recurrence = None
        if result.recurrence is not None:
            recurrence = result.recurrence.model_dump(
                exclude_none=True,
            )

        needs_reminder = (
            intent == "reminder" or remind_iso is not None
        )
        if needs_reminder:
            if remind_iso is None:
                return texts.BAD_DATE
            task, reminder = entities.create_task_with_reminder(
                conn,
                user_id=user["id"],
                title=title,
                description=description,
                due_at=due_iso,
                remind_at=remind_iso,
                recurrence=recurrence,
            )
            return texts.task_created(task, tz_name, reminder)

        task = entities.create_task(
            conn,
            user["id"],
            title,
            description=description,
            due_at=due_iso,
        )
        return texts.task_created(task, tz_name, None)
    except Exception:
        logger.exception("persist intent failed")
        return texts.GENERIC_ERROR
    finally:
        conn.close()
