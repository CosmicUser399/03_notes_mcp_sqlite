"""SQLite repository tests."""

from __future__ import annotations

from app.db.migrate import init_db
from app.db.repositories import feed as feed_repo
from app.db.repositories import notes as notes_repo
from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.db.repositories import users as users_repo
from app.services.clock import to_utc_iso, utc_now
from app.services.recurrence import dumps_rule, next_remind_at


def test_init_db_idempotent(db_path: str, conn) -> None:
    init_db(db_path)
    init_db(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'",
    ).fetchall()
    names = {r["name"] for r in tables}
    assert {"users", "notes", "tasks", "reminders"} <= names


def test_user_note_task_reminder_crud(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        1001,
        "Europe/Berlin",
        "09:00",
    )
    assert user["telegram_user_id"] == 1001
    again = users_repo.upsert_user(
        conn,
        1001,
        "Europe/Berlin",
        "09:00",
    )
    assert again["id"] == user["id"]

    note = notes_repo.create_note(
        conn,
        user["id"],
        "Важно",
        "текст заметки",
    )
    assert note["title"] == "Важно"

    task = tasks_repo.create_task(
        conn,
        user["id"],
        "Позвонить",
        description="Сергею",
    )
    rem = reminders_repo.create_reminder(
        conn,
        task_id=task["id"],
        user_id=user["id"],
        remind_at=to_utc_iso(utc_now()),
    )
    assert rem["status"] == "pending"
    assert rem["task_id"] == task["id"]


def test_feed_order(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        42,
        "Europe/Berlin",
        "09:00",
    )
    notes_repo.create_note(conn, user["id"], "n1", "a")
    tasks_repo.create_task(conn, user["id"], "t1")
    items = feed_repo.list_feed(conn, user["id"], 10)
    assert len(items) >= 2
    assert items[0]["created_at"] >= items[1]["created_at"]


def test_search_notes_by_title(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        7,
        "Europe/Berlin",
        "09:00",
    )
    notes_repo.create_note(conn, user["id"], "важно сегодня", "x")
    notes_repo.create_note(conn, user["id"], "другое", "важно")
    found = notes_repo.search_notes(conn, "важно", field="title")
    assert len(found) == 1
    assert "важно" in found[0]["title"].lower()


def test_claim_cas_and_mark_sent(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        9,
        "Europe/Berlin",
        "09:00",
    )
    task = tasks_repo.create_task(conn, user["id"], "x")
    past = "2000-01-01T00:00:00Z"
    rem = reminders_repo.create_reminder(
        conn,
        task_id=task["id"],
        user_id=user["id"],
        remind_at=past,
    )
    claimed = reminders_repo.claim_due_reminders(
        conn,
        "2020-01-01T00:00:00Z",
    )
    assert len(claimed) == 1
    assert claimed[0]["id"] == rem["id"]
    again = reminders_repo.claim_due_reminders(
        conn,
        "2020-01-01T00:00:00Z",
    )
    assert again == []
    reminders_repo.mark_sent(conn, rem["id"])
    row = reminders_repo.get_reminder(conn, rem["id"])
    assert row is not None
    assert row["status"] == "sent"


def test_next_remind_monthly_clamp() -> None:
    # Jan 31 -> Feb last day
    rule = dumps_rule(
        {"freq": "monthly", "interval": 1, "bymonthday": 31},
    )
    nxt = next_remind_at(
        "2024-01-31T08:00:00Z",
        rule,
        "UTC",
    )
    assert nxt.startswith("2024-02-29")


def test_next_remind_daily() -> None:
    rule = dumps_rule({"freq": "daily", "interval": 1})
    nxt = next_remind_at(
        "2024-03-01T10:00:00Z",
        rule,
        "UTC",
    )
    assert nxt == "2024-03-02T10:00:00Z"
