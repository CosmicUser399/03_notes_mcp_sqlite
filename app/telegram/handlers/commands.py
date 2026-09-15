"""Command handlers: /start, create shortcuts, lists."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import get_settings
from app.db.connection import get_connection
from app.db.repositories import feed as feed_repo
from app.telegram import texts
from app.telegram.fsm import CreateStates
from app.telegram.helpers import ensure_user

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Welcome and upsert user."""
    await state.clear()
    if message.from_user is None:
        return
    settings = get_settings()
    ensure_user(settings, message.from_user.id)
    await message.answer(texts.START_TEXT)


@router.message(Command("note"))
async def cmd_note(message: Message, state: FSMContext) -> None:
    """Start explicit note creation."""
    if message.from_user is None:
        return
    ensure_user(get_settings(), message.from_user.id)
    await state.set_state(CreateStates.waiting_for_text)
    await state.update_data(forced_intent="note")
    await message.answer(texts.ASK_NOTE)


@router.message(Command("task"))
async def cmd_task(message: Message, state: FSMContext) -> None:
    """Start explicit task creation."""
    if message.from_user is None:
        return
    ensure_user(get_settings(), message.from_user.id)
    await state.set_state(CreateStates.waiting_for_text)
    await state.update_data(forced_intent="task")
    await message.answer(texts.ASK_TASK)


@router.message(Command("reminder"))
async def cmd_reminder(
    message: Message,
    state: FSMContext,
) -> None:
    """Start explicit reminder creation."""
    if message.from_user is None:
        return
    ensure_user(get_settings(), message.from_user.id)
    await state.set_state(CreateStates.waiting_for_text)
    await state.update_data(forced_intent="reminder")
    await message.answer(texts.ASK_REMINDER)


async def _list_n(message: Message, limit: int) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    user = ensure_user(settings, message.from_user.id)
    conn = get_connection()
    try:
        items = feed_repo.list_feed(conn, user["id"], limit)
    finally:
        conn.close()
    await message.answer(texts.format_feed(items))


@router.message(Command("list_5"))
async def cmd_list_5(message: Message) -> None:
    """Show 5 latest feed items."""
    await _list_n(message, 5)


@router.message(Command("list_10"))
async def cmd_list_10(message: Message) -> None:
    """Show 10 latest feed items."""
    await _list_n(message, 10)
