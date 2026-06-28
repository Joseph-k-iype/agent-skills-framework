"""FalkorDB connection factory + thin query wrapper.

FalkorDB speaks the Redis protocol; the official `falkordb` Python client wraps a
redis connection pool. We keep a process-wide client and select one graph.
"""

from __future__ import annotations

from typing import Any

from falkordb import FalkorDB

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("graph")

_db: FalkorDB | None = None


def get_db() -> FalkorDB:
    global _db
    if _db is None:
        _db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
    return _db


def get_graph():
    """Return the selected graph handle (FastAPI dependency-friendly)."""
    return get_db().select_graph(settings.falkordb_graph)


def query(cypher: str, params: dict[str, Any] | None = None):
    """Run a read/write Cypher query against the configured graph."""
    return get_graph().query(cypher, params or {})


def ro_query(cypher: str, params: dict[str, Any] | None = None):
    """Run a read-only Cypher query (lets FalkorDB route to replicas if any)."""
    g = get_graph()
    # ro_query exists on recent clients; fall back to query otherwise.
    fn = getattr(g, "ro_query", None)
    return fn(cypher, params or {}) if fn else g.query(cypher, params or {})


def ping() -> bool:
    """Liveness check used by /readyz — does a trivial graph roundtrip."""
    try:
        res = query("RETURN 1 AS ok")
        return bool(res.result_set and res.result_set[0][0] == 1)
    except Exception as exc:  # pragma: no cover - surfaced via /readyz
        log.warning("falkordb_ping_failed", error=str(exc))
        return False


def node_to_dict(node: Any) -> dict[str, Any]:
    """Normalize a FalkorDB node (or already-dict) to a plain properties dict."""
    if node is None:
        return {}
    if isinstance(node, dict):
        return dict(node)
    props = getattr(node, "properties", None)
    return dict(props) if props is not None else dict(node)


def reset_client() -> None:
    """Drop the cached client (used by tests)."""
    global _db
    _db = None
