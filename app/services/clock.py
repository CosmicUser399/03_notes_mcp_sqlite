"""UTC clock helpers and timezone conversion."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """Return current UTC datetime with tzinfo."""
    return datetime.now(timezone.utc)


def to_utc_iso(dt: datetime) -> str:
    """Serialize datetime as UTC ISO-8601 with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc_iso(value: str) -> datetime:
    """Parse UTC ISO string into aware datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local_to_utc(dt_local: datetime, tz_name: str) -> datetime:
    """Convert naive or local datetime to UTC."""
    tz = ZoneInfo(tz_name)
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=tz)
    else:
        dt_local = dt_local.astimezone(tz)
    return dt_local.astimezone(timezone.utc)


def utc_to_local(dt_utc: datetime, tz_name: str) -> datetime:
    """Convert UTC datetime to user timezone."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(ZoneInfo(tz_name))


def parse_hhmm(value: str) -> time:
    """Parse HH:MM time string."""
    hour_s, minute_s = value.strip().split(":", 1)
    return time(hour=int(hour_s), minute=int(minute_s))


def tomorrow_at_default(
    tz_name: str,
    default_hhmm: str,
    now_utc: datetime | None = None,
) -> datetime:
    """Return tomorrow at default reminder time in UTC."""
    now = now_utc or utc_now()
    local_now = utc_to_local(now, tz_name)
    target_date = local_now.date() + timedelta(days=1)
    local_dt = datetime.combine(
        target_date,
        parse_hhmm(default_hhmm),
        tzinfo=ZoneInfo(tz_name),
    )
    return local_dt.astimezone(timezone.utc)


def format_local(dt_utc: datetime, tz_name: str) -> str:
    """Human-readable local datetime for bot replies."""
    local = utc_to_local(dt_utc, tz_name)
    return local.strftime("%d.%m.%Y %H:%M")
