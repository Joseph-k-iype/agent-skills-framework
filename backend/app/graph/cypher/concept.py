"""Parametrized Cypher for the Concept projection (workspace bundle → graph).

Concepts are keyed by ``key = "<workspace_id>::<path>"`` so a file's identity is
its location in the bundle. The projection is rebuilt from files; it is never the
source of truth.
"""

from __future__ import annotations

UPSERT_CONCEPT = """
MERGE (c:Concept {key:$key})
SET c.workspace_id = $workspace_id, c.path = $path,
    c.name = $title, c.title = $title, c.type = $type,
    c.description = $description, c.runtime = $runtime,
    c.tags = $tags, c.capabilities = $capabilities,
    c.body = $body, c.content_hash = $content_hash, c.status = 'active',
    c.created_at = coalesce(c.created_at, $ts), c.updated_at = $ts
RETURN c
"""

SET_EMBEDDING = "MATCH (c:Concept {key:$key}) SET c.embedding = vecf32($vec)"

CREATE_REFERENCE = """
MATCH (a:Concept {key:$from_key}), (b:Concept {key:$to_key})
MERGE (a)-[:REFERENCES]->(b)
"""

DELETE_CONCEPT = "MATCH (c:Concept {key:$key}) DETACH DELETE c"

CLEAR_WORKSPACE = "MATCH (c:Concept {workspace_id:$workspace_id}) DETACH DELETE c"

CONTENT_HASH = "MATCH (c:Concept {key:$key}) RETURN c.content_hash AS h"

GET_CONCEPT = """
MATCH (c:Concept {key:$key})
OPTIONAL MATCH (c)-[:REFERENCES]->(ref:Concept)
RETURN c, collect(DISTINCT {path:ref.path, title:ref.title, type:ref.type}) AS refs
"""

LIST_CONCEPTS = """
MATCH (c:Concept {workspace_id:$workspace_id})
RETURN c ORDER BY c.path LIMIT $limit
"""

COUNT_CONCEPTS = "MATCH (c:Concept {workspace_id:$workspace_id}) RETURN count(c) AS n"

COUNT_REFERENCES = """
MATCH (:Concept {workspace_id:$workspace_id})-[r:REFERENCES]->(:Concept)
RETURN count(r) AS n
"""

# Neighborhood for the relationship-mode graph view.
NEIGHBORHOOD = """
MATCH (c:Concept {key:$key})
OPTIONAL MATCH (c)-[:REFERENCES]->(out:Concept)
OPTIONAL MATCH (inc:Concept)-[:REFERENCES]->(c)
RETURN c,
  collect(DISTINCT {dir:'out', path:out.path, title:out.title, type:out.type}) AS outgoing,
  collect(DISTINCT {dir:'in', path:inc.path, title:inc.title, type:inc.type}) AS incoming
"""
