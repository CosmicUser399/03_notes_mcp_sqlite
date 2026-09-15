"""Aiogram bot entrypoint."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from app.config import get_settings
from app.db.migrate import init_db
from app.telegram.handlers import setup_routers
from app.telegram.scheduler import start_scheduler

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(
        command="start",
        description="Приветствие и инструкция",
    ),
    BotCommand(
        command="note",
        description="Создать заметку",
    ),
    BotCommand(
        command="task",
        description="Создать задачу",
    ),
    BotCommand(
        command="reminder",
        description="Создать напоминание",
    ),
    BotCommand(
        command="list_5",
        description="5 последних записей",
    ),
    BotCommand(
        command="list_10",
        description="10 последних записей",
    ),
]


async def register_bot_commands(bot: Bot) -> None:
    """Publish command menu in Telegram clients."""
    await bot.set_my_commands(BOT_COMMANDS)
    logger.info("bot commands registered (%s)", len(BOT_COMMANDS))


async def main() -> None:
    """Run polling bot with reminder scheduler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    init_db()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.exception(
            "handler error: %s",
            event.exception,
        )
        return True

    await register_bot_commands(bot)
    scheduler = start_scheduler(bot, settings)
    try:
        logger.info("bot polling started")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
