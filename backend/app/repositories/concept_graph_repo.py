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
        sources: list[str],
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
                "sources": sources,
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

    def mark_embedding_pending(self, *, workspace_id: str, path: str) -> None:
        client.query(Q.MARK_EMBEDDING_PENDING, {"key": make_key(workspace_id, path)})

    def pending_embedding_paths(self, workspace_id: str) -> list[str]:
        rows = _rows(client.ro_query(Q.PENDING_EMBEDDINGS, {"workspace_id": workspace_id}))
        return [r[0] for r in rows if r and r[0]]

    def clear_references_from(self, *, workspace_id: str, path: str) -> None:
        client.query(Q.CLEAR_REFERENCES_FROM, {"key": make_key(workspace_id, path)})

    def create_reference(self, *, workspace_id: str, from_path: str, to_path: str) -> None:
        client.query(
            Q.CREATE_REFERENCE,
            {
                "from_key": make_key(workspace_id, from_path),
                "to_key": make_key(workspace_id, to_path),
            },
        )

    def clear_uses_from(self, *, workspace_id: str, path: str) -> None:
        """Drop all outgoing USES (→Capability) edges from a concept node."""
        client.query(Q.CLEAR_USES_FROM, {"key": make_key(workspace_id, path)})

    def clear_derived_from_from(self, *, workspace_id: str, path: str) -> None:
        """Drop all outgoing DERIVED_FROM (→Source) edges from a concept node."""
        client.query(Q.CLEAR_DERIVED_FROM_FROM, {"key": make_key(workspace_id, path)})

    def create_uses(self, *, workspace_id: str, path: str, term_key: str) -> None:
        """Create a USES edge from a concept to a Capability term."""
        client.query(
            Q.CREATE_USES,
            {"concept_key": make_key(workspace_id, path), "term_key": term_key},
        )

    def create_derived_from(self, *, workspace_id: str, path: str, term_key: str) -> None:
        """Create a DERIVED_FROM edge from a concept to a Source term."""
        client.query(
            Q.CREATE_DERIVED_FROM,
            {"concept_key": make_key(workspace_id, path), "term_key": term_key},
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
        results = vector.query_nodes("Concept", embedding, k, only_ok=True)
        out: list[tuple[dict, float]] = []
        for props, score in results:
            props.pop("embedding", None)
            if props.get("workspace_id") == workspace_id:
                out.append((props, score))
        return out

    def graph(self, workspace_id: str) -> dict:
        """All concept nodes + REFERENCES edges for the workspace graph view."""
        rows = _rows(client.ro_query(Q.WORKSPACE_GRAPH, {"workspace_id": workspace_id}))
        nodes = []
        edges = []
        for path, title, ctype, description, runtime, versions, targets in rows:
            nodes.append(
                {
                    "path": path,
                    "title": title,
                    "type": ctype,
                    "description": description,
                    "runtime": runtime,
                    "versions": int(versions or 0),
                }
            )
            for t in targets or []:
                if t:
                    edges.append({"source": path, "target": t})
        return {"nodes": nodes, "edges": edges}

    def analytics(self, workspace_id: str) -> dict:
        """Graph-shape insights for the dashboard: types, hubs, orphans, totals."""
        types = [
            {"type": r[0], "count": int(r[1])}
            for r in _rows(client.ro_query(Q.TYPE_COUNTS, {"workspace_id": workspace_id}))
        ]
        hubs = [
            {"path": r[0], "title": r[1], "degree": int(r[2])}
            for r in _rows(client.ro_query(Q.HUBS, {"workspace_id": workspace_id, "limit": 8}))
        ]
        orphans = [
            {"path": r[0], "title": r[1]}
            for r in _rows(client.ro_query(Q.ORPHANS, {"workspace_id": workspace_id, "limit": 20}))
        ]
        return {
            "concepts": self.count(workspace_id),
            "references": self.count_references(workspace_id),
            "types": types,
            "hubs": hubs,
            "orphans": orphans,
        }

    def upsert_version(
        self, *, workspace_id: str, path: str, version: str, tag: str, ts: str
    ) -> None:
        client.query(
            Q.UPSERT_VERSION,
            {
                "concept_key": make_key(workspace_id, path),
                "version_key": f"{make_key(workspace_id, path)}::v{version}",
                "workspace_id": workspace_id,
                "path": path,
                "version": version,
                "tag": tag,
                "ts": ts,
            },
        )

    def versions_for(self, *, workspace_id: str, path: str) -> list[dict]:
        rows = _rows(client.ro_query(Q.VERSIONS_FOR, {"key": make_key(workspace_id, path)}))
        return [{"version": r[0], "tag": r[1], "ts": r[2]} for r in rows]

    def neighborhood(self, *, workspace_id: str, path: str) -> dict | None:
        rows = _rows(client.ro_query(Q.NEIGHBORHOOD, {"key": make_key(workspace_id, path)}))
        if not rows:
            return None
        node = client.node_to_dict(rows[0][0])
        node.pop("embedding", None)
        outgoing = [e for e in (rows[0][1] or []) if e.get("path")]
        incoming = [e for e in (rows[0][2] or []) if e.get("path")]
        return {"node": node, "edges": outgoing + incoming}
