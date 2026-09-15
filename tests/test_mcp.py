"""MCP tool and health endpoint tests."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from app.api import mcp_tools
from app.db.connection import get_connection
from app.db.repositories import notes as notes_repo
from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.db.repositories import users as users_repo
from app.services.clock import to_utc_iso, utc_now


def test_health(db_path: str) -> None:
    from app.api.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_mcp_list_and_describe(db_path: str) -> None:
    tables = mcp_tools.list_tables()
    assert "notes" in tables
    cols = mcp_tools.describe_table("notes")
    names = {c["name"] for c in cols}
    assert "title" in names
    assert "text" in names


def test_mcp_describe_unknown(db_path: str) -> None:
    try:
        mcp_tools.describe_table("secrets")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_mcp_notes_scenarios(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        user = users_repo.upsert_user(
            conn,
            1,
            "Europe/Berlin",
            "09:00",
        )
        notes_repo.create_note(
            conn,
            user["id"],
            "важно: отчёт",
            "body",
        )
        task = tasks_repo.create_task(conn, user["id"], "call")
        soon = to_utc_iso(utc_now() + timedelta(hours=2))
        reminders_repo.create_reminder(
            conn,
            task_id=task["id"],
            user_id=user["id"],
            remind_at=soon,
        )
    finally:
        conn.close()

    recent = mcp_tools.list_notes(created_within_days=3)
    assert len(recent) >= 1

    found = mcp_tools.search_notes("важно", field="title")
    assert len(found) >= 1

    upcoming = mcp_tools.list_reminders(upcoming_hours=24)
    assert len(upcoming) >= 1
