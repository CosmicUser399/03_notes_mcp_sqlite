"""Plain-text reply templates for Telegram."""

from __future__ import annotations

from typing import Any

from app.services.clock import format_local, parse_utc_iso

START_TEXT = """Привет! Я бот для заметок, задач и напоминаний.

Пишите обычным текстом — я сам определю тип записи.

Примеры:
• Идея: добавить AI-рекомендации в онбординг
• Позвонить Ивану завтра в 10
• Напомни завтра в 15:00 отправить договор
• Каждый понедельник в 9 отправлять отчёт

Команды:
/note — создать заметку
/task — создать задачу
/reminder — создать напоминание
/list_5 — 5 последних записей
/list_10 — 10 последних записей
"""

ASK_NOTE = "Отправьте текст заметки."
ASK_TASK = "Опишите задачу (можно со сроком)."
ASK_REMINDER = "О чём напомнить и когда?"
ASK_SNOOZE_CUSTOM = "Укажите дату и время для напоминания."
EMPTY_FEED = "Пока нет записей."
UNKNOWN_INTENT = (
    "Не понял запрос. Напишите заметку, задачу "
    "или напоминание."
)
PARSE_ERROR = (
    "Сейчас не могу разобрать сообщение, "
    "попробуйте позже."
)
BAD_DATE = (
    "Не понял дату или время. "
    "Переформулируйте, пожалуйста."
)
GENERIC_ERROR = "Произошла ошибка. Попробуйте ещё раз."
SEND_TEXT_PLEASE = (
    "Пожалуйста, отправьте текстовое сообщение."
)
BUTTON_STALE = "Кнопка устарела."
DONE_OK = "Готово. Задача отмечена выполненной."
DONE_RECURRING = (
    "Отметил. Следующее напоминание запланировано."
)
SNOOZE_OK = "Перенёс напоминание."


def note_created(note: dict[str, Any]) -> str:
    """Confirmation for a saved note."""
    return (
        f"✅ Заметка сохранена\n"
        f"«{note['title']}»"
    )


def task_created(
    task: dict[str, Any],
    tz_name: str,
    reminder: dict[str, Any] | None = None,
) -> str:
    """Confirmation for task / task+reminder."""
    lines = ["✅ Задача создана", task["title"]]
    if reminder is not None:
        when = format_local(
            parse_utc_iso(reminder["remind_at"]),
            tz_name,
        )
        lines.append(f"🔔 Напомню {when}")
    elif task.get("due_at"):
        when = format_local(
            parse_utc_iso(task["due_at"]),
            tz_name,
        )
        lines.append(f"📅 {when}")
    return "\n".join(lines)


def reminder_notification(task_title: str) -> str:
    """Body of a fired reminder message."""
    return f"🔔 Напоминание\n{task_title}"


def format_feed_item(item: dict[str, Any]) -> str:
    """One line in /list_N feed."""
    etype = item["entity_type"]
    if etype == "note":
        return f"📝 {item['title']}"
    if etype == "task":
        return f"☑️ {item['title']}"
    return f"🔔 {item['title']} @ {item['body']}"


def format_feed(items: list[dict[str, Any]]) -> str:
    """Full feed reply."""
    if not items:
        return EMPTY_FEED
    lines = [format_feed_item(i) for i in items]
    return "\n".join(lines)
