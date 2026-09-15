"""Inline keyboards for reminders and snooze."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def reminder_actions(reminder_id: int) -> InlineKeyboardMarkup:
    """Done / snooze buttons under a fired reminder."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Готово",
                    callback_data=f"d:{reminder_id}",
                ),
                InlineKeyboardButton(
                    text="⏰ Напомнить позже",
                    callback_data=f"s:{reminder_id}",
                ),
            ]
        ]
    )


def snooze_menu(reminder_id: int) -> InlineKeyboardMarkup:
    """Snooze preset options."""
    rid = reminder_id
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="15 минут",
                    callback_data=f"s:{rid}:15m",
                ),
                InlineKeyboardButton(
                    text="1 час",
                    callback_data=f"s:{rid}:1h",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="3 часа",
                    callback_data=f"s:{rid}:3h",
                ),
                InlineKeyboardButton(
                    text="Завтра",
                    callback_data=f"s:{rid}:tmr",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Выбрать дату и время",
                    callback_data=f"s:{rid}:custom",
                ),
            ],
        ]
    )
