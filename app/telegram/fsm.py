"""FSM states for explicit create and snooze flows."""

from aiogram.fsm.state import State, StatesGroup


class CreateStates(StatesGroup):
    """Waiting for text after /note|/task|/reminder."""

    waiting_for_text = State()


class SnoozeStates(StatesGroup):
    """Waiting for custom snooze datetime."""

    waiting_for_datetime = State()
