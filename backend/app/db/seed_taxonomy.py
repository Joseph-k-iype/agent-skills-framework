"""Seed the canonical Capability and Source taxonomy terms into FalkorDB.

``seed_taxonomy`` is idempotent — every upsert uses MERGE under the hood, so
running it twice yields the same node count and the same graph state.

The CANONICAL dict maps node-label → ordered list of (key, parent_key) pairs.
Parents always appear before their children so the PARENT_OF edges can be wired
in a single pass.

``label`` (display name) is derived from the last dot-segment, title-cased.
``description`` is left None for all canonical terms.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.repositories.taxonomy_repo import TaxonomyRepository

log = get_logger("seed_taxonomy")

# Ordered: parents before children within each label.
CANONICAL: dict[str, list[tuple[str, str | None]]] = {
    "Capability": [
        ("extraction", None),
        ("extraction.table", "extraction"),
        ("extraction.entity", "extraction"),
        ("transformation", None),
        ("transformation.normalize", "transformation"),
        ("transformation.geocode", "transformation"),
        ("enrichment", None),
        ("validation", None),
        ("classification", None),
        ("generation", None),
        ("redaction", None),
    ],
    "Source": [
        ("file", None),
        ("file.csv", "file"),
        ("file.pdf", "file"),
        ("database", None),
        ("database.postgres", "database"),
        ("api", None),
        ("api.rest", "api"),
        ("stream", None),
        ("stream.kafka", "stream"),
        ("web", None),
        ("web.scrape", "web"),
    ],
}


def _display_label(key: str) -> str:
    """Title-case the last dot-segment of a key.  e.g. 'extraction.table' → 'Table'."""
    return key.split(".")[-1].title()


async def seed_taxonomy(graph=None) -> int:
    """Ensure every canonical term exists in FalkorDB.

    Parameters
    ----------
    graph:
        Accepted for call-site compatibility (e.g. startup code that passes a
        graph name, tests that pass ``graph_name``), but the TaxonomyRepository
        always delegates to the module-level ``app.graph.client`` singleton.

    Returns
    -------
    int
        Total number of canonical terms upserted (same on every idempotent run).
    """
    repo = TaxonomyRepository(graph)
    count = 0
    for node_label, terms in CANONICAL.items():
        for key, parent_key in terms:
            await repo.upsert_term(
                label=node_label,
                key=key,
                term_label=_display_label(key),
                description=None,
                status="canonical",
                parent_key=parent_key,
            )
            count += 1
    log.info("seed_taxonomy_complete", total=count)
    return count
