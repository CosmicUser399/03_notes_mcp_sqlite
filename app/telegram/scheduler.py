"""Background reminder scheduler."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.db.connection import get_connection
from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.db.repositories import users as users_repo
from app.services.clock import to_utc_iso, utc_now
from app.services.recurrence import next_remind_at
from app.telegram import texts
from app.telegram.keyboards import reminder_actions

logger = logging.getLogger(__name__)


async def process_due_reminders(
    bot: Bot,
    settings: Settings,
) -> None:
    """Claim due reminders and send Telegram notifications."""
    now = utc_now()
    now_iso = to_utc_iso(now)
    stuck_before = to_utc_iso(
        now - timedelta(minutes=settings.stuck_processing_minutes),
    )

    conn = get_connection()
    try:
        reminders_repo.recover_stuck_processing(
            conn,
            stuck_before,
        )
        claimed = reminders_repo.claim_due_reminders(
            conn,
            now_iso,
        )
    finally:
        conn.close()

    for rem in claimed:
        await _send_one(bot, rem)


async def _send_one(bot: Bot, rem: dict) -> None:
    rem_id = rem["id"]
    conn = get_connection()
    try:
        user = users_repo.get_by_id(conn, rem["user_id"])
        task = tasks_repo.get_task(conn, rem["task_id"])
        if user is None or task is None:
            reminders_repo.cancel_reminder(conn, rem_id)
            return
        chat_id = user["telegram_user_id"]
        title = task["title"]
    finally:
        conn.close()

    try:
        await bot.send_message(
            chat_id,
            texts.reminder_notification(title),
            reply_markup=reminder_actions(rem_id),
        )
    except Exception:
        logger.exception(
            "failed to send reminder id=%s",
            rem_id,
        )
        conn = get_connection()
        try:
            reminders_repo.release_to_pending(conn, rem_id)
        finally:
            conn.close()
        return

    conn = get_connection()
    try:
        rem = reminders_repo.get_reminder(conn, rem_id)
        if rem is None:
            return
        user = users_repo.get_by_id(conn, rem["user_id"])
        tz_name = (
            user["timezone"] if user else "UTC"
        )
        if rem.get("recurrence_rule"):
            try:
                nxt = next_remind_at(
                    rem["remind_at"],
                    rem["recurrence_rule"],
                    tz_name,
                )
                reminders_repo.reschedule_recurring(
                    conn,
                    rem_id,
                    nxt,
                )
            except Exception:
                logger.exception(
                    "next occurrence failed id=%s",
                    rem_id,
                )
                reminders_repo.cancel_reminder(conn, rem_id)
        else:
            reminders_repo.mark_sent(conn, rem_id)
    finally:
        conn.close()


def start_scheduler(
    bot: Bot,
    settings: Settings,
) -> AsyncIOScheduler:
    """Create and start APScheduler for reminders."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        process_due_reminders,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        args=[bot, settings],
        id="reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "scheduler started interval=%ss",
        settings.scheduler_interval_seconds,
    )
    return scheduler
