"""Aiogram bot entrypoint."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from app.config import get_settings
from app.db.migrate import init_db
from app.telegram.handlers import setup_routers
from app.telegram.scheduler import start_scheduler

logger = logging.getLogger(__name__)


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

    scheduler = start_scheduler(bot, settings)
    try:
        logger.info("bot polling started")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
