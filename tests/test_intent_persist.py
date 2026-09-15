"""Intent persistence without OpenAI (unit)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories import users as users_repo
from app.services.intent import IntentResult
from app.telegram.helpers import persist_intent


def test_persist_note(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        77,
        "Europe/Berlin",
        "09:00",
    )
    # persist_intent opens its own connection via settings path;
    # seed via shared db_path fixture already points settings there.
    result = IntentResult(
        intent="note",
        title="Идея",
        text="добавить рекомендации",
        confidence=0.9,
    )
    reply = persist_intent(user, result)
    assert "Заметка сохранена" in reply


def test_persist_reminder(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        78,
        "Europe/Berlin",
        "09:00",
    )
    when = datetime(2030, 1, 2, 10, 0, tzinfo=timezone.utc)
    result = IntentResult(
        intent="reminder",
        title="Позвонить Сергею",
        text="Позвонить Сергею",
        remind_at=when,
        confidence=0.95,
    )
    reply = persist_intent(user, result)
    assert "Задача создана" in reply
    assert "Напомню" in reply
