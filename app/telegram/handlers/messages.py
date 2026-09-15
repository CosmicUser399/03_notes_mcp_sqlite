"""Free-text and FSM message handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import get_settings
from app.db.connection import get_connection
from app.db.repositories import reminders as reminders_repo
from app.services.clock import (
    local_to_utc,
    to_utc_iso,
    utc_now,
)
from app.services.intent import parse_intent
from app.telegram import texts
from app.telegram.fsm import CreateStates, SnoozeStates
from app.telegram.helpers import apply_intent, ensure_user

router = Router(name="messages")


@router.message(CreateStates.waiting_for_text, F.text)
async def create_text(
    message: Message,
    state: FSMContext,
) -> None:
    """Handle text after /note|/task|/reminder."""
    if message.from_user is None or not message.text:
        return
    data = await state.get_data()
    forced = data.get("forced_intent")
    await state.clear()
    settings = get_settings()
    user = ensure_user(settings, message.from_user.id)
    reply = apply_intent(
        settings,
        user,
        message.text.strip(),
        forced_intent=forced,  # type: ignore[arg-type]
    )
    await message.answer(reply)


@router.message(SnoozeStates.waiting_for_datetime, F.text)
async def snooze_custom_text(
    message: Message,
    state: FSMContext,
) -> None:
    """Parse custom snooze datetime from user text."""
    if message.from_user is None or not message.text:
        return
    data = await state.get_data()
    reminder_id = data.get("snooze_reminder_id")
    await state.clear()
    if reminder_id is None:
        await message.answer(texts.BUTTON_STALE)
        return

    settings = get_settings()
    user = ensure_user(settings, message.from_user.id)
    try:
        result = parse_intent(
            settings,
            message.text.strip(),
            timezone=user["timezone"],
            default_reminder_time=user["default_reminder_time"],
            utc_now_iso=to_utc_iso(utc_now()),
            forced_intent="reminder",
        )
    except Exception:
        await message.answer(texts.PARSE_ERROR)
        return

    when = result.remind_at
    if when is None:
        await message.answer(texts.BAD_DATE)
        return
    if when.tzinfo is None:
        when_utc = local_to_utc(when, user["timezone"])
    else:
        when_utc = when
    remind_iso = to_utc_iso(when_utc)

    conn = get_connection()
    try:
        rem = reminders_repo.get_reminder(conn, int(reminder_id))
        if rem is None or rem["user_id"] != user["id"]:
            await message.answer(texts.BUTTON_STALE)
            return
        reminders_repo.update_remind_at(
            conn,
            int(reminder_id),
            remind_iso,
            status="pending",
        )
    finally:
        conn.close()
    await message.answer(texts.SNOOZE_OK)


@router.message(F.text)
async def free_text(message: Message, state: FSMContext) -> None:
    """Natural language create flow."""
    if message.from_user is None or not message.text:
        return
    current = await state.get_state()
    if current is not None:
        return
    text = message.text.strip()
    if not text:
        await message.answer(texts.SEND_TEXT_PLEASE)
        return
    settings = get_settings()
    user = ensure_user(settings, message.from_user.id)
    reply = apply_intent(settings, user, text)
    await message.answer(reply)


@router.message()
async def non_text(message: Message) -> None:
    """Reject non-text content in MVP."""
    await message.answer(texts.SEND_TEXT_PLEASE)
