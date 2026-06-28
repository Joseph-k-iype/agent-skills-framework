"""Parametrized Cypher for Skill nodes, placement, references, versions.

A skill is identified by a stable ``skill_key``; each version is its own Skill
node. Exactly one node per key carries ``is_current = true``. Version lineage is
expressed with ``(:Skill)-[:PREVIOUS_VERSION]->(:Skill)``.
"""

from __future__ import annotations

CREATE_SKILL = """
MATCH (f:Folder {id:$folder_id})
CREATE (s:Skill {
  id:$id, skill_key:$skill_key, name:$name, type:'Skill',
  description:$description, runtime:$runtime, version:$version,
  status:'draft', is_current:true, workspace_id:$workspace_id,
  folder_id:$folder_id, tags:$tags, capabilities:$capabilities,
  created_at:$ts, updated_at:$ts
})
MERGE (f)-[:HAS_SKILL]->(s)
RETURN s
"""

GET_SKILL = """
MATCH (s:Skill {id:$id})
OPTIONAL MATCH (s)-[:REFERENCES]->(d:OKFDocument)
OPTIONAL MATCH (s)-[:USES]->(c:Capability)
RETURN s,
  collect(DISTINCT {id:d.id, title:d.title}) AS refs,
  collect(DISTINCT c.name) AS capabilities
"""

LIST_CURRENT = """
MATCH (s:Skill) WHERE s.is_current = true
  AND ($workspace_id IS NULL OR s.workspace_id = $workspace_id)
  AND ($folder_id IS NULL OR s.folder_id = $folder_id)
  AND ($q IS NULL OR toLower(s.name) CONTAINS toLower($q))
RETURN s ORDER BY s.updated_at DESC LIMIT $limit
"""

UPDATE_SKILL = """
MATCH (s:Skill {id:$id})
SET s.name = coalesce($name, s.name),
    s.description = coalesce($description, s.description),
    s.runtime = coalesce($runtime, s.runtime),
    s.tags = coalesce($tags, s.tags),
    s.capabilities = coalesce($capabilities, s.capabilities),
    s.updated_at = $ts
RETURN s
"""

SET_STATUS = "MATCH (s:Skill {id:$id}) SET s.status = $status, s.updated_at = $ts RETURN s"

DELETE_SKILL = "MATCH (s:Skill {id:$id}) DETACH DELETE s"

# ── references & capabilities ──
CLEAR_REFERENCES = "MATCH (s:Skill {id:$id})-[r:REFERENCES]->(:OKFDocument) DELETE r"
ADD_REFERENCE = """
MATCH (s:Skill {id:$id}), (d:OKFDocument {id:$doc_id})
MERGE (s)-[:REFERENCES]->(d)
"""

CLEAR_CAPABILITIES = "MATCH (s:Skill {id:$id})-[r:USES]->(:Capability) DELETE r"
ADD_CAPABILITY = """
MATCH (s:Skill {id:$id})
MERGE (c:Capability {name:$name})
  ON CREATE SET c.type = 'Capability', c.created_at = $ts
MERGE (s)-[:USES]->(c)
"""

# ── versioning ──
CLEAR_CURRENT = "MATCH (s:Skill {skill_key:$skill_key}) SET s.is_current = false"

CREATE_VERSION = """
MATCH (old:Skill {id:$old_id})
OPTIONAL MATCH (f:Folder)-[:HAS_SKILL]->(old)
CREATE (s:Skill {
  id:$id, skill_key:old.skill_key, name:old.name, type:'Skill',
  description:old.description, runtime:old.runtime, version:$version,
  status:'published', is_current:true, workspace_id:old.workspace_id,
  folder_id:old.folder_id, tags:old.tags, capabilities:old.capabilities,
  created_at:$ts, updated_at:$ts
})
MERGE (s)-[:PREVIOUS_VERSION]->(old)
WITH s, old, f
FOREACH (_ IN CASE WHEN f IS NULL THEN [] ELSE [1] END | MERGE (f)-[:HAS_SKILL]->(s))
RETURN s
"""

# Copy REFERENCES / USES edges from a previous version to the new node.
COPY_EDGES = """
MATCH (old:Skill {id:$old_id}), (new:Skill {id:$new_id})
OPTIONAL MATCH (old)-[:REFERENCES]->(d:OKFDocument)
FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END | MERGE (new)-[:REFERENCES]->(d))
WITH old, new
OPTIONAL MATCH (old)-[:USES]->(c:Capability)
FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END | MERGE (new)-[:USES]->(c))
"""

VERSION_CHAIN = """
MATCH (s:Skill {skill_key:$skill_key})
RETURN s ORDER BY s.created_at ASC
"""

# ── clone ──
CLONE_SKILL = """
MATCH (src:Skill {id:$src_id}), (f:Folder {id:$folder_id})
CREATE (s:Skill {
  id:$id, skill_key:$skill_key, name:$name, type:'Skill',
  description:src.description, runtime:src.runtime, version:'0.1.0',
  status:'draft', is_current:true, workspace_id:f.workspace_id,
  folder_id:$folder_id, tags:src.tags, capabilities:src.capabilities,
  created_at:$ts, updated_at:$ts
})
MERGE (f)-[:HAS_SKILL]->(s)
RETURN s
"""
