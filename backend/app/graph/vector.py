"""Vector-search helpers over FalkorDB native vector indexes.

Keeps the vector ABI in one place so a brute-force cosine fallback can be
swapped in if a given FalkorDB image lacks ``db.idx.vector.queryNodes``.
"""

from __future__ import annotations

from typing import Any

from app.graph.client import ro_query


def _vecf32(values: list[float]) -> str:
    """Render a Python list as a FalkorDB vecf32 literal."""
    inner = ",".join(repr(float(v)) for v in values)
    return f"vecf32([{inner}])"


def query_nodes(
    label: str,
    embedding: list[float],
    k: int = 10,
) -> list[tuple[dict[str, Any], float]]:
    """Return up to ``k`` nearest nodes of ``label`` with their score.

    Score is the configured similarity metric (cosine). FalkorDB returns a
    distance-like score; callers sort ascending (closer = smaller).
    """
    cypher = (
        f"CALL db.idx.vector.queryNodes('{label}', 'embedding', $k, {_vecf32(embedding)}) "
        "YIELD node, score RETURN node, score ORDER BY score ASC"
    )
    res = ro_query(cypher, {"k": k})
    out: list[tuple[dict[str, Any], float]] = []
    for row in res.result_set:
        node, score = row[0], row[1]
        props = dict(node.properties) if hasattr(node, "properties") else dict(node)
        out.append((props, float(score)))
    return out
