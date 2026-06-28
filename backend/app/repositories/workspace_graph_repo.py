"""FalkorDB-backed persistence for the Workspace + Folder hierarchy.

The graph is the source of truth for workspace structure (PRD). Cypher lives in
``app.graph.cypher.workspace``; this repo binds parameters and normalizes nodes.
"""

from __future__ import annotations

from typing import Any

from app.graph import client
from app.graph.cypher import workspace as Q


def _rows(result) -> list[list[Any]]:
    return result.result_set or []


class WorkspaceGraphRepository:
    # ── workspaces ──
    def create_workspace(self, *, id: str, name: str, description: str | None, owner: str, ts: str) -> dict:
        res = client.query(
            Q.CREATE_WORKSPACE,
            {"id": id, "name": name, "description": description, "owner": owner, "ts": ts},
        )
        return client.node_to_dict(_rows(res)[0][0])

    def list_workspaces(self, *, owner: str, is_admin: bool) -> list[dict]:
        res = client.ro_query(Q.LIST_WORKSPACES_FOR_OWNER, {"owner": owner, "is_admin": is_admin})
        return [client.node_to_dict(r[0]) for r in _rows(res)]

    def get_workspace(self, id: str) -> dict | None:
        rows = _rows(client.ro_query(Q.GET_WORKSPACE, {"id": id}))
        return client.node_to_dict(rows[0][0]) if rows else None

    def update_workspace(self, *, id: str, name: str | None, description: str | None, ts: str) -> dict | None:
        rows = _rows(
            client.query(Q.UPDATE_WORKSPACE, {"id": id, "name": name, "description": description, "ts": ts})
        )
        return client.node_to_dict(rows[0][0]) if rows else None

    def delete_workspace(self, id: str) -> None:
        client.query(Q.DELETE_WORKSPACE, {"id": id})

    def get_subtree(self, id: str) -> list[dict]:
        """Return folders of a workspace as flat records: {**folder, parent_id}."""
        rows = _rows(client.ro_query(Q.GET_SUBTREE, {"id": id}))
        if not rows:
            return []
        out: list[dict] = []
        for rec in rows[0][0] or []:
            folder = rec.get("folder") if isinstance(rec, dict) else None
            if folder is None:
                continue
            d = client.node_to_dict(folder)
            d["parent_id"] = rec.get("parent_id")
            out.append(d)
        return out

    # ── folders ──
    def create_folder(
        self, *, id: str, name: str, path: str, workspace_id: str, parent_id: str, ts: str
    ) -> dict | None:
        rows = _rows(
            client.query(
                Q.CREATE_FOLDER,
                {
                    "id": id,
                    "name": name,
                    "path": path,
                    "workspace_id": workspace_id,
                    "parent_id": parent_id,
                    "ts": ts,
                },
            )
        )
        return client.node_to_dict(rows[0][0]) if rows else None

    def get_folder(self, id: str) -> dict | None:
        rows = _rows(client.ro_query(Q.GET_FOLDER, {"id": id}))
        return client.node_to_dict(rows[0][0]) if rows else None

    def get_children(self, id: str) -> list[dict]:
        rows = _rows(client.ro_query(Q.GET_CHILDREN, {"id": id}))
        return [client.node_to_dict(r[0]) for r in rows]

    def get_parent(self, id: str) -> dict | None:
        rows = _rows(client.ro_query(Q.GET_PARENT, {"id": id}))
        return client.node_to_dict(rows[0][0]) if rows else None

    def get_folder_subtree(self, id: str) -> tuple[dict | None, list[dict]]:
        rows = _rows(client.ro_query(Q.GET_FOLDER_SUBTREE, {"id": id}))
        if not rows:
            return None, []
        root = client.node_to_dict(rows[0][0])
        descendants = [client.node_to_dict(n) for n in (rows[0][1] or [])]
        return root, descendants

    def rename_folder(self, *, id: str, name: str, ts: str) -> dict | None:
        rows = _rows(client.query(Q.UPDATE_FOLDER_NAME, {"id": id, "name": name, "ts": ts}))
        return client.node_to_dict(rows[0][0]) if rows else None

    def set_folder_path(self, *, id: str, path: str, ts: str) -> None:
        client.query(Q.SET_FOLDER_PATH, {"id": id, "path": path, "ts": ts})

    def delete_folder(self, id: str) -> None:
        client.query(Q.DELETE_FOLDER, {"id": id})

    def is_descendant(self, *, id: str, target_id: str) -> bool:
        rows = _rows(client.ro_query(Q.IS_DESCENDANT, {"id": id, "target_id": target_id}))
        return bool(rows and rows[0][0])

    def move_folder(self, *, id: str, new_parent_id: str, ts: str) -> dict | None:
        rows = _rows(client.query(Q.MOVE_FOLDER, {"id": id, "new_parent_id": new_parent_id, "ts": ts}))
        return client.node_to_dict(rows[0][0]) if rows else None
