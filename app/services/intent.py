"""Intent detection via OpenAI Structured Outputs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import Settings

logger = logging.getLogger(__name__)

IntentName = Literal[
    "note",
    "task",
    "reminder",
    "query",
    "unknown",
]


class RecurrenceModel(BaseModel):
    """MVP recurrence rule from the model."""

    freq: Literal["daily", "weekly", "monthly", "yearly"]
    interval: int = 1
    byweekday: list[int] | None = None
    bymonthday: int | None = None


class IntentResult(BaseModel):
    """Structured intent payload."""

    intent: IntentName
    title: str = ""
    text: str = ""
    due_at: datetime | None = None
    remind_at: datetime | None = None
    recurrence: RecurrenceModel | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


SYSTEM_PROMPT = """You classify Russian Telegram messages for a
notes/tasks/reminders bot.

Return structured fields only.
Rules:
- intent=note for ideas/facts to store without action time.
- intent=task for actionable items; set due_at if a deadline
  is stated.
- intent=reminder when user asks to be reminded; always set
  remind_at; also fill title/text of what to remind.
- If date is clear but time is missing for a reminder, use
  default_reminder_time in the user timezone.
- intent=query for read/list questions (bot cannot answer DB
  queries in chat).
- intent=unknown if unclear.
- Do not invent dates that were not implied.
- All datetimes must be timezone-aware in the user timezone
  or as absolute ISO with offset.
Current UTC: {utc_now}
User timezone: {timezone}
Default reminder time: {default_reminder_time}
"""


def parse_intent(
    settings: Settings,
    text: str,
    *,
    timezone: str,
    default_reminder_time: str,
    utc_now_iso: str,
    forced_intent: IntentName | None = None,
) -> IntentResult:
    """Call OpenAI and return structured intent."""
    client = OpenAI(api_key=settings.openai_api_key)
    system = SYSTEM_PROMPT.format(
        utc_now=utc_now_iso,
        timezone=timezone,
        default_reminder_time=default_reminder_time,
    )
    user_content = text
    if forced_intent is not None:
        user_content = (
            f"Forced intent: {forced_intent}. "
            f"Interpret the message accordingly.\n\n{text}"
        )
    try:
        completion = client.beta.chat.completions.parse(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format=IntentResult,
        )
        result = completion.choices[0].message.parsed
        if result is None:
            return IntentResult(intent="unknown", text=text)
        if forced_intent is not None:
            result.intent = forced_intent
        if not result.text:
            result.text = text
        return result
    except Exception:
        logger.exception("OpenAI intent parse failed")
        raise
