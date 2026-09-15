"""Scheduler unit helpers."""

from __future__ import annotations

from datetime import timedelta

from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.db.repositories import users as users_repo
from app.services.clock import to_utc_iso, utc_now


def test_stuck_processing_recovery(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        55,
        "Europe/Berlin",
        "09:00",
    )
    task = tasks_repo.create_task(conn, user["id"], "t")
    rem = reminders_repo.create_reminder(
        conn,
        task_id=task["id"],
        user_id=user["id"],
        remind_at="2000-01-01T00:00:00Z",
    )
    old = to_utc_iso(utc_now() - timedelta(hours=1))
    conn.execute(
        """
        UPDATE reminders
        SET status = 'processing', last_triggered_at = ?
        WHERE id = ?
        """,
        (old, rem["id"]),
    )
    conn.commit()
    n = reminders_repo.recover_stuck_processing(
        conn,
        to_utc_iso(utc_now() - timedelta(minutes=5)),
    )
    assert n == 1
    row = reminders_repo.get_reminder(conn, rem["id"])
    assert row is not None
    assert row["status"] == "pending"


def test_release_on_send_failure_path(conn) -> None:
    user = users_repo.upsert_user(
        conn,
        56,
        "Europe/Berlin",
        "09:00",
    )
    task = tasks_repo.create_task(conn, user["id"], "t")
    rem = reminders_repo.create_reminder(
        conn,
        task_id=task["id"],
        user_id=user["id"],
        remind_at="2000-01-01T00:00:00Z",
    )
    claimed = reminders_repo.claim_due_reminders(
        conn,
        "2020-01-01T00:00:00Z",
    )
    assert claimed
    reminders_repo.release_to_pending(conn, rem["id"])
    row = reminders_repo.get_reminder(conn, rem["id"])
    assert row is not None
    assert row["status"] == "pending"
