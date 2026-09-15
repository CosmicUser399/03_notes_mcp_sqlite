"""Inline callback handlers for done / snooze."""

from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import get_settings
from app.db.connection import get_connection
from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.db.repositories import users as users_repo
from app.services.clock import (
    to_utc_iso,
    tomorrow_at_default,
    utc_now,
)
from app.services.recurrence import next_remind_at
from app.telegram import texts
from app.telegram.fsm import SnoozeStates
from app.telegram.keyboards import snooze_menu

router = Router(name="callbacks")


def _parse_done(data: str) -> int | None:
    if not data.startswith("d:"):
        return None
    try:
        return int(data.split(":", 1)[1])
    except ValueError:
        return None


def _parse_snooze(data: str) -> tuple[int, str | None] | None:
    # s:{id} or s:{id}:15m|1h|3h|tmr|custom
    parts = data.split(":")
    if len(parts) < 2 or parts[0] != "s":
        return None
    try:
        rem_id = int(parts[1])
    except ValueError:
        return None
    preset = parts[2] if len(parts) >= 3 else None
    return rem_id, preset


@router.callback_query(F.data.startswith("d:"))
async def on_done(callback: CallbackQuery) -> None:
    """Mark task done / advance recurring reminder."""
    if callback.from_user is None or not callback.data:
        return
    rem_id = _parse_done(callback.data)
    if rem_id is None:
        await callback.answer(texts.BUTTON_STALE)
        return

    conn = get_connection()
    try:
        rem = reminders_repo.get_reminder(conn, rem_id)
        if rem is None:
            await callback.answer(texts.BUTTON_STALE)
            return
        user = users_repo.get_by_id(conn, rem["user_id"])
        if user is None:
            await callback.answer(texts.BUTTON_STALE)
            return
        # ownership: telegram id must match
        if user["telegram_user_id"] != callback.from_user.id:
            await callback.answer(texts.BUTTON_STALE)
            return

        if rem.get("recurrence_rule"):
            # Scheduler already moved remind_at forward after send.
            # Done only acknowledges this occurrence.
            if rem["status"] in ("pending", "processing"):
                # Edge case: fired but not yet rescheduled
                if rem["status"] == "processing":
                    try:
                        nxt = next_remind_at(
                            rem["remind_at"],
                            rem["recurrence_rule"],
                            user["timezone"],
                        )
                        reminders_repo.reschedule_recurring(
                            conn,
                            rem_id,
                            nxt,
                        )
                    except Exception:
                        reminders_repo.cancel_reminder(
                            conn,
                            rem_id,
                        )
                        tasks_repo.complete_task(
                            conn,
                            rem["task_id"],
                        )
                        await callback.answer()
                        if callback.message:
                            await callback.message.answer(
                                texts.DONE_OK,
                            )
                        return
            msg = texts.DONE_RECURRING
        else:
            tasks_repo.complete_task(conn, rem["task_id"])
            reminders_repo.cancel_active_for_task(
                conn,
                rem["task_id"],
            )
            reminders_repo.cancel_reminder(conn, rem_id)
            msg = texts.DONE_OK
    finally:
        conn.close()

    await callback.answer()
    if callback.message:
        await callback.message.answer(msg)


@router.callback_query(F.data.startswith("s:"))
async def on_snooze(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Show snooze menu or apply preset."""
    if callback.from_user is None or not callback.data:
        return
    parsed = _parse_snooze(callback.data)
    if parsed is None:
        await callback.answer(texts.BUTTON_STALE)
        return
    rem_id, preset = parsed

    conn = get_connection()
    try:
        rem = reminders_repo.get_reminder(conn, rem_id)
        if rem is None:
            await callback.answer(texts.BUTTON_STALE)
            return
        user = users_repo.get_by_id(conn, rem["user_id"])
        if (
            user is None
            or user["telegram_user_id"] != callback.from_user.id
        ):
            await callback.answer(texts.BUTTON_STALE)
            return

        if preset is None:
            await callback.answer()
            if callback.message:
                await callback.message.answer(
                    "Когда напомнить?",
                    reply_markup=snooze_menu(rem_id),
                )
            return

        if preset == "custom":
            await state.set_state(
                SnoozeStates.waiting_for_datetime,
            )
            await state.update_data(snooze_reminder_id=rem_id)
            await callback.answer()
            if callback.message:
                await callback.message.answer(
                    texts.ASK_SNOOZE_CUSTOM,
                )
            return

        now = utc_now()
        if preset == "15m":
            when = now + timedelta(minutes=15)
        elif preset == "1h":
            when = now + timedelta(hours=1)
        elif preset == "3h":
            when = now + timedelta(hours=3)
        elif preset == "tmr":
            when = tomorrow_at_default(
                user["timezone"],
                user["default_reminder_time"],
                now_utc=now,
            )
        else:
            await callback.answer(texts.BUTTON_STALE)
            return

        reminders_repo.update_remind_at(
            conn,
            rem_id,
            to_utc_iso(when),
            status="pending",
        )
    finally:
        conn.close()

    await callback.answer()
    if callback.message:
        await callback.message.answer(texts.SNOOZE_OK)
