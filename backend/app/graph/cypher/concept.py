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
    c.embedding_status = coalesce(c.embedding_status, 'pending'),
    c.created_at = coalesce(c.created_at, $ts), c.updated_at = $ts
RETURN c
"""

# A real embedding is searchable. vecf32($vec) with a list parameter is supported
# by the FalkorDB build in use (verified against the live graph).
SET_EMBEDDING = (
    "MATCH (c:Concept {key:$key}) SET c.embedding = vecf32($vec), c.embedding_status = 'ok'"
)

# Mark a node's embedding as pending (degraded/failed) without storing a vector,
# so it is excluded from search and picked up by the heal/reindex pass.
MARK_EMBEDDING_PENDING = "MATCH (c:Concept {key:$key}) SET c.embedding_status = 'pending'"

# Paths whose embedding still needs (re)computing.
PENDING_EMBEDDINGS = """
MATCH (c:Concept {workspace_id:$workspace_id})
WHERE c.embedding_status IS NULL OR c.embedding_status <> 'ok'
RETURN c.path AS path ORDER BY path
"""

CREATE_REFERENCE = """
MATCH (a:Concept {key:$from_key}), (b:Concept {key:$to_key})
MERGE (a)-[:REFERENCES]->(b)
"""

# Drop a node's outgoing references so a re-index can recreate them cleanly
# (otherwise stale edges accumulate across edits).
CLEAR_REFERENCES_FROM = "MATCH (a:Concept {key:$key})-[r:REFERENCES]->() DELETE r"

DELETE_CONCEPT = "MATCH (c:Concept {key:$key}) DETACH DELETE c"

# Drop the whole projection for a workspace — concept nodes AND their version nodes.
CLEAR_WORKSPACE = (
    "MATCH (n) WHERE (n:Concept OR n:Version) AND n.workspace_id = $workspace_id "
    "DETACH DELETE n"
)

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

WORKSPACE_GRAPH = """
MATCH (c:Concept {workspace_id:$workspace_id})
OPTIONAL MATCH (c)-[:REFERENCES]->(t:Concept {workspace_id:$workspace_id})
OPTIONAL MATCH (c)-[:HAS_VERSION]->(v:Version)
RETURN c.path AS path, c.title AS title, c.type AS type,
       c.description AS description, c.runtime AS runtime,
       count(DISTINCT v) AS versions,
       collect(DISTINCT t.path) AS targets
ORDER BY path
"""

# ── published versions (one Version node per publish tag) ──
UPSERT_VERSION = """
MATCH (c:Concept {key:$concept_key})
MERGE (v:Version {key:$version_key})
SET v.workspace_id = $workspace_id, v.path = $path, v.version = $version,
    v.tag = $tag, v.ts = $ts
MERGE (c)-[:HAS_VERSION]->(v)
RETURN v
"""

VERSIONS_FOR = """
MATCH (c:Concept {key:$key})-[:HAS_VERSION]->(v:Version)
RETURN v.version AS version, v.tag AS tag, v.ts AS ts
ORDER BY v.ts DESC
"""

COUNT_CONCEPTS = "MATCH (c:Concept {workspace_id:$workspace_id}) RETURN count(c) AS n"

TYPE_COUNTS = """
MATCH (c:Concept {workspace_id:$workspace_id})
RETURN c.type AS type, count(c) AS n ORDER BY n DESC
"""

HUBS = """
MATCH (c:Concept {workspace_id:$workspace_id})
OPTIONAL MATCH (c)-[r:REFERENCES]-()
RETURN c.path AS path, c.title AS title, count(r) AS degree
ORDER BY degree DESC LIMIT $limit
"""

ORPHANS = """
MATCH (c:Concept {workspace_id:$workspace_id})
WHERE NOT (c)-[:REFERENCES]-()
RETURN c.path AS path, c.title AS title ORDER BY path LIMIT $limit
"""

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
