"""Handlers package."""

from aiogram import Router

from app.telegram.handlers.callbacks import router as cb_router
from app.telegram.handlers.commands import router as cmd_router
from app.telegram.handlers.messages import router as msg_router


def setup_routers() -> Router:
    """Aggregate all Telegram routers."""
    root = Router()
    root.include_router(cmd_router)
    root.include_router(cb_router)
    root.include_router(msg_router)
    return root
