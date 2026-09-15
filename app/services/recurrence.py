"""Recurrence next-occurrence helpers for MVP."""

from __future__ import annotations

import json
from datetime import timezone
from typing import Any
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from app.services.clock import parse_utc_iso, to_utc_iso, utc_to_local

ALLOWED_FREQ = frozenset({"daily", "weekly", "monthly", "yearly"})


def parse_rule(raw: str | None) -> dict[str, Any] | None:
    """Parse recurrence_rule JSON text."""
    if raw is None or not str(raw).strip():
        return None
    data = json.loads(raw)
    freq = str(data.get("freq", "")).lower()
    if freq not in ALLOWED_FREQ:
        raise ValueError(f"unsupported freq: {freq}")
    return {
        "freq": freq,
        "interval": int(data.get("interval", 1) or 1),
        "byweekday": data.get("byweekday"),
        "bymonthday": data.get("bymonthday"),
    }


def dumps_rule(rule: dict[str, Any]) -> str:
    """Serialize recurrence rule to JSON text."""
    payload: dict[str, Any] = {
        "freq": rule["freq"],
        "interval": int(rule.get("interval", 1)),
    }
    if rule.get("byweekday") is not None:
        payload["byweekday"] = rule["byweekday"]
    if rule.get("bymonthday") is not None:
        payload["bymonthday"] = rule["bymonthday"]
    return json.dumps(payload, ensure_ascii=False)


def next_remind_at(
    current_remind_at: str,
    rule_raw: str,
    tz_name: str,
) -> str:
    """
    Compute next UTC remind_at after current occurrence.

    Monthly day clamping: if bymonthday is 31 and the next
    month has fewer days, use the last day of that month.
    """
    rule = parse_rule(rule_raw)
    if rule is None:
        raise ValueError("empty recurrence rule")
    current = parse_utc_iso(current_remind_at)
    local = utc_to_local(current, tz_name)
    interval = max(1, int(rule["interval"]))
    freq = rule["freq"]
    tz = ZoneInfo(tz_name)

    if freq == "daily":
        nxt = local + relativedelta(days=interval)
    elif freq == "weekly":
        byweekday = rule.get("byweekday")
        if byweekday:
            target = int(byweekday[0])
            nxt = local + relativedelta(days=1)
            while nxt.weekday() != target:
                nxt = nxt + relativedelta(days=1)
            weeks = interval - 1
            if weeks > 0:
                nxt = nxt + relativedelta(weeks=weeks)
        else:
            nxt = local + relativedelta(weeks=interval)
    elif freq == "monthly":
        day = int(rule.get("bymonthday") or local.day)
        nxt = local + relativedelta(months=interval)
        last_day = (nxt + relativedelta(day=31)).day
        use_day = min(day, last_day)
        nxt = nxt.replace(day=use_day)
    elif freq == "yearly":
        nxt = local + relativedelta(years=interval)
    else:
        raise ValueError(f"unsupported freq: {freq}")

    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=tz)
    else:
        nxt = nxt.astimezone(tz)
    return to_utc_iso(nxt.astimezone(timezone.utc))
