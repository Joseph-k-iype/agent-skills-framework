"""Parametrized Cypher for the Taxonomy layer (Capability and Source term nodes).

Terms are global (not workspace-scoped) and keyed by ``(label, key)`` where
``key`` is a human-readable slug (e.g. "extraction.table").  Hierarchy between
terms of the same label is expressed via ``(:Label)-[:PARENT_OF]->(:Label)``.

``$label`` is always the FalkorDB node-label string, passed as a literal in the
calling Python (the Cypher template uses ``apoc``-style dynamic label syntax
supported by FalkorDB via the ``label()`` function on the MERGE).

FalkorDB does not support dynamic node labels in MERGE via a parameter, so the
repository layer substitutes the label into the query string before execution.
The caller is responsible for validating the label string against the known set
``{"Capability", "Source"}`` before interpolation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# NOTE: {label} is a format-string placeholder — NOT a Cypher $param.
# TaxonomyRepository fills it in via .format(label=...) after validating the
# label against the allowed set {"Capability", "Source"}.
# ---------------------------------------------------------------------------

# MERGE a term node; set all mutable props; optionally set created_at once.
UPSERT_TERM = """
MERGE (t:{label} {{key: $key}})
SET t.key = $key,
    t.label = $term_label,
    t.description = $description,
    t.status = $status,
    t.created_at = coalesce(t.created_at, $ts),
    t.updated_at = $ts
RETURN t
"""

# MERGE the PARENT_OF relationship between two same-label terms.
SET_PARENT = """
MATCH (parent:{label} {{key: $parent_key}})
MATCH (child:{label}  {{key: $child_key}})
MERGE (parent)-[:PARENT_OF]->(child)
"""

# Fetch a single term by key.
GET_TERM = """
MATCH (t:{label} {{key: $key}})
RETURN t
"""

# All terms of a given label with their optional parent key.
LIST_TREE = """
MATCH (t:{label})
OPTIONAL MATCH (p:{label})-[:PARENT_OF]->(t)
RETURN t, p.key AS parent_key
ORDER BY t.key
"""

# All terms across both labels with status = "proposed".
LIST_PROPOSED = """
MATCH (t)
WHERE (t:Capability OR t:Source) AND t.status = 'proposed'
RETURN t, labels(t)[0] AS node_label
ORDER BY t.key
"""

# Flip a term's status to canonical.
PROMOTE = """
MATCH (t:{label} {{key: $key}})
SET t.status = 'canonical'
RETURN t
"""

# Repoint Concept USES/DERIVED_FROM edges that point at alias → into_key node,
# reparent any same-label children of the alias to into,
# then delete the alias node.  Returns nothing on success.
REPOINT_AND_DELETE_ALIAS = """
MATCH (alias:{label} {{key: $alias_key}})
MATCH (into:{label}  {{key: $into_key}})

// --- reparent hierarchy children (Fix I2) ---
OPTIONAL MATCH (alias)-[pc:PARENT_OF]->(child:{label})
FOREACH (rel IN CASE WHEN pc IS NOT NULL THEN [pc] ELSE [] END |
    DELETE rel
)
WITH alias, into, collect(child) AS children
FOREACH (ch IN children |
    MERGE (into)-[:PARENT_OF]->(ch)
)

// --- repoint USES edges (Fix M4) ---
WITH alias, into
OPTIONAL MATCH (c1:Concept)-[r1:USES]->(alias)
FOREACH (rel IN CASE WHEN r1 IS NOT NULL THEN [r1] ELSE [] END |
    DELETE rel
)
WITH alias, into, collect(c1) AS uses_concepts

FOREACH (c IN uses_concepts |
    MERGE (c)-[:USES]->(into)
)

// --- repoint DERIVED_FROM edges (Fix M4) ---
WITH alias, into
OPTIONAL MATCH (c2:Concept)-[r2:DERIVED_FROM]->(alias)
FOREACH (rel IN CASE WHEN r2 IS NOT NULL THEN [r2] ELSE [] END |
    DELETE rel
)
WITH alias, into, collect(c2) AS derived_concepts

FOREACH (c IN derived_concepts |
    MERGE (c)-[:DERIVED_FROM]->(into)
)

// --- delete the alias (no remaining edges due to explicit deletions above) ---
WITH alias
DETACH DELETE alias
"""
