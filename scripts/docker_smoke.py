"""Docker/integration smoke tests against shared SQLite volume."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Run inside api container: python /tmp/docker_smoke.py


def connect() -> sqlite3.Connection:
    path = os.environ.get("SQLITE_PATH", "/data/notes.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    from app.api import mcp_tools
    from app.db.repositories import notes as notes_repo
    from app.db.repositories import reminders as reminders_repo
    from app.db.repositories import tasks as tasks_repo
    from app.db.repositories import users as users_repo

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    # 1. Schema tables exist
    conn = connect()
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        needed = {"users", "notes", "tasks", "reminders"}
        check("schema_tables", needed <= tables, str(sorted(tables)))

        # 2. Seed data for MCP scenarios
        user = users_repo.upsert_user(
            conn,
            telegram_user_id=900001,
            timezone="Europe/Berlin",
            default_reminder_time="09:00",
        )
        note = notes_repo.create_note(
            conn,
            user["id"],
            "важно: docker smoke",
            "проверка MCP через Docker",
        )
        task = tasks_repo.create_task(
            conn,
            user["id"],
            "Позвонить из Docker",
            description="smoke",
        )
        soon = utc_iso(datetime.now(timezone.utc) + timedelta(hours=2))
        rem = reminders_repo.create_reminder(
            conn,
            task_id=task["id"],
            user_id=user["id"],
            remind_at=soon,
        )
        check("seed_note", note["id"] > 0, f"id={note['id']}")
        check("seed_reminder", rem["status"] == "pending", rem["remind_at"])
    finally:
        conn.close()

    # 3. MCP tools (4 mandatory scenarios)
    tables_list = mcp_tools.list_tables()
    check("mcp_list_tables", set(tables_list) >= needed, str(tables_list))

    cols = mcp_tools.describe_table("notes")
    col_names = {c["name"] for c in cols}
    check("mcp_describe_notes", "title" in col_names and "text" in col_names)

    recent = mcp_tools.list_notes(created_within_days=3)
    check(
        "mcp_list_notes_3d",
        any(n.get("title", "").startswith("важно") for n in recent),
        f"count={len(recent)}",
    )

    found = mcp_tools.search_notes("важно", field="title")
    check("mcp_search_title", len(found) >= 1, f"count={len(found)}")

    upcoming = mcp_tools.list_reminders(upcoming_hours=24)
    check(
        "mcp_reminders_24h",
        any(r["id"] == rem["id"] for r in upcoming),
        f"count={len(upcoming)}",
    )

    # 4. describe_table whitelist
    try:
        mcp_tools.describe_table("no_such_table")
        check("mcp_whitelist", False, "expected ValueError")
    except ValueError:
        check("mcp_whitelist", True)

    # 5. CAS claim for due reminder (near-term)
    conn = connect()
    try:
        past = utc_iso(datetime.now(timezone.utc) - timedelta(minutes=1))
        due_task = tasks_repo.create_task(conn, user["id"], "due now")
        due_rem = reminders_repo.create_reminder(
            conn,
            task_id=due_task["id"],
            user_id=user["id"],
            remind_at=past,
        )
        claimed = reminders_repo.claim_due_reminders(
            conn,
            utc_iso(datetime.now(timezone.utc)),
        )
        ids = {c["id"] for c in claimed}
        check("cas_claim", due_rem["id"] in ids, f"claimed={ids}")
        # release so bot scheduler can retry later if needed
        reminders_repo.release_to_pending(conn, due_rem["id"])
        # push far future to avoid Telegram spam during smoke
        far = utc_iso(datetime.now(timezone.utc) + timedelta(days=30))
        reminders_repo.update_remind_at(conn, due_rem["id"], far)
    finally:
        conn.close()

    failed = [r for r in results if not r[1]]
    print("---")
    print(f"total={len(results)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
