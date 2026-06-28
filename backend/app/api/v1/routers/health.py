"""Liveness + readiness probes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.envelope import success
from app.db.session import engine
from app.graph.client import ping as graph_ping

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    """Liveness — process is up."""
    return success({"status": "ok"})


@router.get("/readyz")
async def readyz():
    """Readiness — Postgres reachable and FalkorDB roundtrip works."""
    pg_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pg_ok = True
    except Exception:
        pg_ok = False

    graph_ok = graph_ping()
    ready = pg_ok and graph_ok
    return success(
        {"ready": ready, "postgres": pg_ok, "falkordb": graph_ok},
        meta={"degraded": not ready},
    )
