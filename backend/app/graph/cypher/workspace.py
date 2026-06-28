"""Parametrized Cypher for Workspace + Folder hierarchy.

The hierarchy uses a single directed edge type: ``(:Workspace|Folder)-[:CONTAINS]->(:Folder)``.
User input is always passed via ``$params`` — never string-formatted into Cypher.
"""

from __future__ import annotations

CREATE_WORKSPACE = """
CREATE (w:Workspace {
  id:$id, name:$name, type:'Workspace', description:$description,
  owner:$owner, status:'active', created_at:$ts, updated_at:$ts
})
RETURN w
"""

LIST_WORKSPACES_FOR_OWNER = """
MATCH (w:Workspace) WHERE w.owner = $owner OR $is_admin
RETURN w ORDER BY w.created_at DESC
"""

GET_WORKSPACE = "MATCH (w:Workspace {id:$id}) RETURN w"

UPDATE_WORKSPACE = """
MATCH (w:Workspace {id:$id})
SET w.name = coalesce($name, w.name),
    w.description = coalesce($description, w.description),
    w.updated_at = $ts
RETURN w
"""

DELETE_WORKSPACE = """
MATCH (w:Workspace {id:$id})
OPTIONAL MATCH (w)-[:CONTAINS*]->(n)
DETACH DELETE w, n
"""

# Full folder subtree of a workspace, each with its direct parent id.
GET_SUBTREE = """
MATCH (w:Workspace {id:$id})
OPTIONAL MATCH (w)-[:CONTAINS]->(top:Folder)
OPTIONAL MATCH (w)-[:CONTAINS*]->(f:Folder)
OPTIONAL MATCH (p)-[:CONTAINS]->(f)
RETURN collect(DISTINCT {folder:f, parent_id: p.id}) AS rows
"""

# ── folders ──
CREATE_FOLDER = """
MATCH (parent {id:$parent_id})
WHERE parent:Workspace OR parent:Folder
CREATE (f:Folder {
  id:$id, name:$name, type:'Folder', path:$path,
  workspace_id:$workspace_id, status:'active', created_at:$ts, updated_at:$ts
})
MERGE (parent)-[:CONTAINS]->(f)
RETURN f
"""

GET_FOLDER = "MATCH (f:Folder {id:$id}) RETURN f"

# Direct children of a container (workspace or folder).
GET_CHILDREN = """
MATCH (parent {id:$id})-[:CONTAINS]->(child)
RETURN child ORDER BY child.name
"""

# Subtree of a folder (the folder itself + all descendants) for path recompute.
GET_FOLDER_SUBTREE = """
MATCH (root:Folder {id:$id})
OPTIONAL MATCH (root)-[:CONTAINS*]->(d:Folder)
RETURN root, collect(DISTINCT d) AS descendants
"""

UPDATE_FOLDER_NAME = """
MATCH (f:Folder {id:$id})
SET f.name = $name, f.updated_at = $ts
RETURN f
"""

SET_FOLDER_PATH = "MATCH (f:Folder {id:$id}) SET f.path = $path, f.updated_at = $ts"

DELETE_FOLDER = """
MATCH (f:Folder {id:$id})
OPTIONAL MATCH (f)-[:CONTAINS*]->(d)
DETACH DELETE f, d
"""

# Cycle guard: is target a descendant of (or equal to) the folder being moved?
IS_DESCENDANT = """
MATCH (f:Folder {id:$id})
OPTIONAL MATCH (f)-[:CONTAINS*]->(d:Folder {id:$target_id})
RETURN (f.id = $target_id) OR (d IS NOT NULL) AS blocked
"""

# Reparent: drop current incoming CONTAINS edge, attach to the new parent.
MOVE_FOLDER = """
MATCH (f:Folder {id:$id})
OPTIONAL MATCH (old)-[r:CONTAINS]->(f) DELETE r
WITH f
MATCH (np {id:$new_parent_id}) WHERE np:Workspace OR np:Folder
MERGE (np)-[:CONTAINS]->(f)
SET f.updated_at = $ts
RETURN f
"""

# Direct parent of a folder (workspace or folder).
GET_PARENT = "MATCH (p)-[:CONTAINS]->(f:Folder {id:$id}) RETURN p"
