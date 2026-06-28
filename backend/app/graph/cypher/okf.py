"""Parametrized Cypher for OKF documents, references and graph exploration."""

from __future__ import annotations

UPSERT_DOCUMENT = """
MERGE (d:OKFDocument {id:$id})
SET d.name = $title, d.title = $title, d.type = $type,
    d.relative_path = $relative_path, d.source_repository = $source_repository,
    d.body = $body, d.tags = $tags, d.workspace_id = $workspace_id,
    d.content_hash = $content_hash, d.status = 'active',
    d.created_at = coalesce(d.created_at, $ts), d.updated_at = $ts
RETURN d
"""

LINK_TO_FOLDER = """
MATCH (f:Folder {id:$folder_id}), (d:OKFDocument {id:$id})
MERGE (f)-[:HAS_DOCUMENT]->(d)
MERGE (d)-[:BELONGS_TO]->(f)
"""

CREATE_REFERENCE = """
MATCH (a:OKFDocument {id:$from_id}), (b:OKFDocument {id:$to_id})
MERGE (a)-[:REFERENCES]->(b)
"""

SET_EMBEDDING = "MATCH (d:OKFDocument {id:$id}) SET d.embedding = vecf32($vec)"

GET_DOCUMENT = """
MATCH (d:OKFDocument {id:$id})
OPTIONAL MATCH (d)-[:REFERENCES]->(ref:OKFDocument)
OPTIONAL MATCH (d)-[:BELONGS_TO]->(f:Folder)
RETURN d, collect(DISTINCT {id:ref.id, title:ref.title}) AS refs, f.id AS folder_id
"""

CONTENT_HASH = "MATCH (d:OKFDocument {id:$id}) RETURN d.content_hash AS h"

LIST_DOCUMENTS = """
MATCH (d:OKFDocument)
WHERE $workspace_id IS NULL OR d.workspace_id = $workspace_id
RETURN d ORDER BY d.updated_at DESC LIMIT $limit
"""

# Neighborhood of a node for the relationship-mode graph view.
NEIGHBORHOOD = """
MATCH (n {id:$id})
OPTIONAL MATCH (n)-[r]->(m)
WHERE m:OKFDocument OR m:Skill OR m:Folder OR m:Capability
RETURN n,
  collect(DISTINCT {
    rel:type(r), dir:'out', id:m.id,
    label:coalesce(m.title, m.name), kind:labels(m)[0]
  }) AS outgoing
"""

INCOMING = """
MATCH (m)-[r]->(n {id:$id})
WHERE m:OKFDocument OR m:Skill OR m:Folder OR m:Capability
RETURN collect(DISTINCT {
  rel:type(r), dir:'in', id:m.id,
  label:coalesce(m.title, m.name), kind:labels(m)[0]
}) AS incoming
"""
