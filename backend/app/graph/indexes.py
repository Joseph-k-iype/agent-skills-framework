"""Idempotent FalkorDB index bootstrap — range indexes + vector indexes.

Called once at application startup. FalkorDB raises if an index already exists,
so each statement is guarded. Vector indexes power semantic search; the
dimension MUST match ``settings.embedding_dim`` everywhere a vector is written.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.graph.client import query
from app.graph.ontology import EMBEDDABLE_LABELS, NodeLabel

log = get_logger("graph.indexes")

# (label, property) range indexes for fast lookup / uniqueness-style access.
_RANGE_INDEXES: tuple[tuple[str, str], ...] = (
    (NodeLabel.WORKSPACE, "id"),
    (NodeLabel.KNOWLEDGE_PACKAGE, "id"),
    (NodeLabel.FOLDER, "id"),
    (NodeLabel.FOLDER, "workspace_id"),
    (NodeLabel.SKILL, "id"),
    (NodeLabel.SKILL, "workspace_id"),
    (NodeLabel.OKF_DOCUMENT, "id"),
    (NodeLabel.OKF_DOCUMENT, "relative_path"),
    (NodeLabel.CONCEPT, "key"),
    (NodeLabel.CONCEPT, "workspace_id"),
    (NodeLabel.CAPABILITY, "name"),
)


def _safe(cypher: str) -> None:
    try:
        query(cypher)
    except Exception as exc:  # already-exists or unsupported — log and continue
        msg = str(exc).lower()
        if "already" in msg or "exist" in msg:
            return
        log.warning("index_bootstrap_stmt_failed", cypher=cypher, error=str(exc))


def bootstrap_indexes() -> None:
    for label, prop in _RANGE_INDEXES:
        _safe(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")

    dim = settings.embedding_dim
    for label in EMBEDDABLE_LABELS:
        _safe(
            f"CREATE VECTOR INDEX FOR (n:{label}) ON (n.embedding) "
            f"OPTIONS {{dimension:{dim}, similarityFunction:'cosine'}}"
        )
    log.info("graph_indexes_bootstrapped", embedding_dim=dim)
