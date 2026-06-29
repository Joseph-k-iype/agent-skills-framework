"""FalkorDB persistence for the Concept projection.

Nodes are keyed by ``key = "<workspace_id>::<path>"``. This repo only writes the
projection; the markdown files in the workspace bundle remain the source of truth.
"""

from __future__ import annotations

from typing import Any

from app.graph import client, vector
from app.graph.cypher import concept as Q


def make_key(workspace_id: str, path: str) -> str:
    return f"{workspace_id}::{path}"


def _rows(result) -> list[list[Any]]:
    return result.result_set or []


class ConceptGraphRepository:
    def upsert_concept(
        self,
        *,
        workspace_id: str,
        path: str,
        title: str,
        type: str,
        description: str | None,
        runtime: str | None,
        tags: list[str],
        capabilities: list[str],
        body: str,
        content_hash: str,
        ts: str,
    ) -> dict:
        res = client.query(
            Q.UPSERT_CONCEPT,
            {
                "key": make_key(workspace_id, path),
                "workspace_id": workspace_id,
                "path": path,
                "title": title,
                "type": type,
                "description": description,
                "runtime": runtime,
                "tags": tags,
                "capabilities": capabilities,
                "body": body,
                "content_hash": content_hash,
                "ts": ts,
            },
        )
        return client.node_to_dict(_rows(res)[0][0])

    def existing_hash(self, *, workspace_id: str, path: str) -> str | None:
        rows = _rows(client.ro_query(Q.CONTENT_HASH, {"key": make_key(workspace_id, path)}))
        return rows[0][0] if rows and rows[0][0] else None

    def set_embedding(self, *, workspace_id: str, path: str, vec: list[float]) -> None:
        client.query(Q.SET_EMBEDDING, {"key": make_key(workspace_id, path), "vec": vec})

    def create_reference(self, *, workspace_id: str, from_path: str, to_path: str) -> None:
        client.query(
            Q.CREATE_REFERENCE,
            {
                "from_key": make_key(workspace_id, from_path),
                "to_key": make_key(workspace_id, to_path),
            },
        )

    def delete_concept(self, *, workspace_id: str, path: str) -> None:
        client.query(Q.DELETE_CONCEPT, {"key": make_key(workspace_id, path)})

    def clear_workspace(self, workspace_id: str) -> None:
        client.query(Q.CLEAR_WORKSPACE, {"workspace_id": workspace_id})

    def count(self, workspace_id: str) -> int:
        rows = _rows(client.ro_query(Q.COUNT_CONCEPTS, {"workspace_id": workspace_id}))
        return int(rows[0][0]) if rows else 0

    def count_references(self, workspace_id: str) -> int:
        rows = _rows(client.ro_query(Q.COUNT_REFERENCES, {"workspace_id": workspace_id}))
        return int(rows[0][0]) if rows else 0

    def get_concept(self, *, workspace_id: str, path: str) -> dict | None:
        rows = _rows(client.ro_query(Q.GET_CONCEPT, {"key": make_key(workspace_id, path)}))
        if not rows:
            return None
        d = client.node_to_dict(rows[0][0])
        d.pop("embedding", None)
        d["references"] = [r for r in (rows[0][1] or []) if r.get("path")]
        return d

    def list_concepts(self, *, workspace_id: str, limit: int = 500) -> list[dict]:
        params = {"workspace_id": workspace_id, "limit": limit}
        rows = _rows(client.ro_query(Q.LIST_CONCEPTS, params))
        out = []
        for r in rows:
            d = client.node_to_dict(r[0])
            d.pop("embedding", None)
            out.append(d)
        return out

    def search(
        self, *, workspace_id: str, embedding: list[float], k: int
    ) -> list[tuple[dict, float]]:
        results = vector.query_nodes("Concept", embedding, k)
        out: list[tuple[dict, float]] = []
        for props, score in results:
            props.pop("embedding", None)
            if props.get("workspace_id") == workspace_id:
                out.append((props, score))
        return out

    def neighborhood(self, *, workspace_id: str, path: str) -> dict | None:
        rows = _rows(client.ro_query(Q.NEIGHBORHOOD, {"key": make_key(workspace_id, path)}))
        if not rows:
            return None
        node = client.node_to_dict(rows[0][0])
        node.pop("embedding", None)
        outgoing = [e for e in (rows[0][1] or []) if e.get("path")]
        incoming = [e for e in (rows[0][2] or []) if e.get("path")]
        return {"node": node, "edges": outgoing + incoming}
