"""Clock and timezone helpers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.clock import (
    format_local,
    local_to_utc,
    parse_utc_iso,
    to_utc_iso,
)


def test_utc_roundtrip() -> None:
    local = datetime(2024, 6, 1, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    utc = local_to_utc(local, "Europe/Berlin")
    iso = to_utc_iso(utc)
    assert iso.endswith("Z")
    back = parse_utc_iso(iso)
    assert to_utc_iso(back) == iso
    human = format_local(back, "Europe/Berlin")
    assert "01.06.2024" in human
