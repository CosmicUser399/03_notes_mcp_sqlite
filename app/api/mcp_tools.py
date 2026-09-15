"""MCP tool implementations (read-only)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from app.db.connection import get_connection
from app.db.migrate import init_db
from app.db.repositories import notes as notes_repo
from app.db.repositories import reminders as reminders_repo
from app.db.repositories import tasks as tasks_repo
from app.services.clock import to_utc_iso, utc_now

ALLOWED_TABLES = frozenset({"users", "notes", "tasks", "reminders"})

mcp = FastMCP(
    "notes-sqlite",
    stateless_http=True,
    streamable_http_path="/",
)


def _ensure_db() -> None:
    init_db()


@mcp.tool()
def list_tables() -> list[str]:
    """List user tables available in the notes database."""
    _ensure_db()
    return sorted(ALLOWED_TABLES)


@mcp.tool()
def describe_table(table_name: str) -> list[dict[str, Any]]:
    """Describe columns of a whitelisted table."""
    _ensure_db()
    name = table_name.strip().lower()
    if name not in ALLOWED_TABLES:
        raise ValueError(
            f"Unknown table '{table_name}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_TABLES))}"
        )
    conn = get_connection()
    try:
        rows = conn.execute(
            f"PRAGMA table_info({name})",
        ).fetchall()
        fks = conn.execute(
            f"PRAGMA foreign_key_list({name})",
        ).fetchall()
        fk_by_col = {
            r["from"]: {
                "table": r["table"],
                "to": r["to"],
            }
            for r in fks
        }
        result: list[dict[str, Any]] = []
        for row in rows:
            col: dict[str, Any] = {
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "pk": bool(row["pk"]),
                "default": row["dflt_value"],
            }
            if row["name"] in fk_by_col:
                col["fk"] = fk_by_col[row["name"]]
            result.append(col)
        return result
    finally:
        conn.close()


@mcp.tool()
def list_notes(
    date_from: str | None = None,
    date_to: str | None = None,
    created_within_days: int | None = None,
    order: Literal["asc", "desc"] = "desc",
    limit: int = 20,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    """List notes with optional date filters."""
    _ensure_db()
    df = date_from
    dt = date_to
    if created_within_days is not None:
        days = max(0, int(created_within_days))
        df = to_utc_iso(utc_now() - timedelta(days=days))
    conn = get_connection()
    try:
        return notes_repo.list_notes(
            conn,
            date_from=df,
            date_to=dt,
            order=order,
            limit=limit,
            include_archived=include_archived,
        )
    finally:
        conn.close()


@mcp.tool()
def search_notes(
    query: str,
    field: Literal["title", "text", "both"] = "title",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search notes by title and/or text substring."""
    _ensure_db()
    if not query.strip():
        return []
    conn = get_connection()
    try:
        return notes_repo.search_notes(
            conn,
            query.strip(),
            field=field,
            limit=limit,
        )
    finally:
        conn.close()


@mcp.tool()
def list_tasks(
    status: Literal["open", "completed"] | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List tasks with optional status and due filters."""
    _ensure_db()
    conn = get_connection()
    try:
        return tasks_repo.list_tasks(
            conn,
            status=status,
            due_from=due_from,
            due_to=due_to,
            limit=limit,
        )
    finally:
        conn.close()


@mcp.tool()
def list_reminders(
    remind_from: str | None = None,
    remind_to: str | None = None,
    upcoming_hours: int | None = None,
    status: (
        Literal["pending", "processing", "sent", "cancelled"]
        | None
    ) = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List reminders; upcoming_hours sets a window from now."""
    _ensure_db()
    rf = remind_from
    rt = remind_to
    if upcoming_hours is not None:
        hours = max(0, int(upcoming_hours))
        now = utc_now()
        rf = to_utc_iso(now)
        rt = to_utc_iso(now + timedelta(hours=hours))
    conn = get_connection()
    try:
        return reminders_repo.list_reminders(
            conn,
            remind_from=rf,
            remind_to=rt,
            status=status,
            limit=limit,
        )
    finally:
        conn.close()
