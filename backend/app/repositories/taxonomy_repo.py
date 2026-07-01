"""FalkorDB persistence for Capability and Source taxonomy terms.

Terms are global (not workspace-scoped) and keyed by a slug ``key`` unique
per node label.  The repository validates that ``label`` is one of the two
known strings before interpolating it into Cypher — FalkorDB does not support
dynamic node labels via parameters, so interpolation is the only option.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.graph import client
from app.graph.cypher import taxonomy as Q

# The only labels this repository knows about.
_ALLOWED_LABELS: frozenset[str] = frozenset({"Capability", "Source"})


def _rows(result) -> list[list[Any]]:
    return result.result_set or []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_label(label: str) -> str:
    """Raise ValueError for unknown labels; return the label on success."""
    if label not in _ALLOWED_LABELS:
        raise ValueError(
            f"Unknown taxonomy label {label!r}. Must be one of {sorted(_ALLOWED_LABELS)}."
        )
    return label


class TaxonomyRepository:
    """Thin FalkorDB accessor for Capability / Source term nodes.

    The constructor accepts an optional ``graph`` argument for forward
    compatibility with dependency-injection patterns, but the repository
    always delegates to the module-level ``app.graph.client`` singleton —
    exactly as every other repository in this codebase does.
    """

    def __init__(self, graph=None) -> None:  # noqa: ANN001 — graph kept for compat
        # graph is accepted but not used; kept so call-sites can pass it.
        pass

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    async def upsert_term(
        self,
        label: str,
        key: str,
        term_label: str,
        description: str | None,
        status: str,
        parent_key: str | None,
    ) -> dict:
        """MERGE a term node; optionally wire PARENT_OF from parent."""
        _validate_label(label)
        ts = _now_iso()
        res = client.query(
            Q.UPSERT_TERM.format(label=label),
            {
                "key": key,
                "term_label": term_label,
                "description": description,
                "status": status,
                "ts": ts,
            },
        )
        rows = _rows(res)
        node = client.node_to_dict(rows[0][0]) if rows else {}

        if parent_key:
            client.query(
                Q.SET_PARENT.format(label=label),
                {"parent_key": parent_key, "child_key": key},
            )

        return node

    async def get_term(self, label: str, key: str) -> dict | None:
        """Return the term dict or None if not found."""
        _validate_label(label)
        rows = _rows(client.ro_query(Q.GET_TERM.format(label=label), {"key": key}))
        if not rows:
            return None
        return client.node_to_dict(rows[0][0])

    async def list_tree(self, label: str) -> list[dict]:
        """All terms of *label*, each with a ``parent_key`` field (None if root)."""
        _validate_label(label)
        rows = _rows(client.ro_query(Q.LIST_TREE.format(label=label), {}))
        out: list[dict] = []
        for row in rows:
            d = client.node_to_dict(row[0])
            d["parent_key"] = row[1]  # None when no PARENT_OF edge exists
            out.append(d)
        return out

    async def list_proposed(self) -> list[dict]:
        """Terms across both labels where status = 'proposed'."""
        rows = _rows(client.ro_query(Q.LIST_PROPOSED, {}))
        out: list[dict] = []
        for row in rows:
            d = client.node_to_dict(row[0])
            # row[1] carries the node label string returned by labels(t)[0]
            d.setdefault("node_label", row[1] if len(row) > 1 else None)
            out.append(d)
        return out

    async def promote(self, label: str, key: str) -> dict | None:
        """Set status = 'canonical'; return the updated term or None."""
        _validate_label(label)
        rows = _rows(client.query(Q.PROMOTE.format(label=label), {"key": key}))
        if not rows:
            return None
        return client.node_to_dict(rows[0][0])

    async def merge_term(self, label: str, key: str, into_key: str) -> bool:
        """Repoint Concept edges from *key* (alias) to *into_key*, delete alias.

        Returns False if the target term (*into_key*) does not exist.
        """
        _validate_label(label)
        # Guard: make sure the target exists before we destroy the alias.
        into = await self.get_term(label, into_key)
        if into is None:
            return False
        client.query(
            Q.REPOINT_AND_DELETE_ALIAS.format(label=label),
            {"alias_key": key, "into_key": into_key},
        )
        return True
