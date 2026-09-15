"""FastAPI application with health and MCP mount."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.mcp_tools import mcp
from app.db.migrate import init_db

logger = logging.getLogger(__name__)

# Build MCP ASGI app first so session_manager exists
mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Init SQLite and MCP session manager."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    init_db()
    logger.info("API started, SQLite initialized")
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Notes MCP API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


app.mount("/mcp", mcp_app)
