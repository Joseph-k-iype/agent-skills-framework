"""FalkorDB persistence for OKF documents, references and neighborhood queries."""

from __future__ import annotations

from typing import Any

from app.graph import client, vector
from app.graph.cypher import okf as Q


def _rows(result) -> list[list[Any]]:
    return result.result_set or []


class OkfGraphRepository:
    def upsert_document(
        self,
        *,
        id: str,
        title: str,
        type: str,
        relative_path: str,
        source_repository: str,
        body: str,
        tags: list[str],
        workspace_id: str | None,
        content_hash: str,
        ts: str,
    ) -> dict:
        res = client.query(
            Q.UPSERT_DOCUMENT,
            {
                "id": id,
                "title": title,
                "type": type,
                "relative_path": relative_path,
                "source_repository": source_repository,
                "body": body,
                "tags": tags,
                "workspace_id": workspace_id,
                "content_hash": content_hash,
                "ts": ts,
            },
        )
        return client.node_to_dict(_rows(res)[0][0])

    def existing_hash(self, id: str) -> str | None:
        rows = _rows(client.ro_query(Q.CONTENT_HASH, {"id": id}))
        return rows[0][0] if rows and rows[0][0] else None

    def link_to_folder(self, *, id: str, folder_id: str) -> None:
        client.query(Q.LINK_TO_FOLDER, {"id": id, "folder_id": folder_id})

    def create_reference(self, *, from_id: str, to_id: str) -> None:
        client.query(Q.CREATE_REFERENCE, {"from_id": from_id, "to_id": to_id})

    def set_embedding(self, *, id: str, vec: list[float]) -> None:
        client.query(Q.SET_EMBEDDING, {"id": id, "vec": vec})

    def get_document(self, id: str) -> dict | None:
        rows = _rows(client.ro_query(Q.GET_DOCUMENT, {"id": id}))
        if not rows:
            return None
        d = client.node_to_dict(rows[0][0])
        d.pop("embedding", None)  # never ship the vector to clients
        d["references"] = [r for r in (rows[0][1] or []) if r.get("id")]
        d["folder_id"] = rows[0][2]
        return d

    def list_documents(self, *, workspace_id: str | None, limit: int = 200) -> list[dict]:
        rows = _rows(
            client.ro_query(Q.LIST_DOCUMENTS, {"workspace_id": workspace_id, "limit": limit})
        )
        out = []
        for r in rows:
            d = client.node_to_dict(r[0])
            d.pop("embedding", None)
            out.append(d)
        return out

    def search(self, *, embedding: list[float], k: int) -> list[tuple[dict, float]]:
        results = vector.query_nodes("OKFDocument", embedding, k)
        for props, _ in results:
            props.pop("embedding", None)
        return results

    def neighborhood(self, id: str) -> dict | None:
        out_rows = _rows(client.ro_query(Q.NEIGHBORHOOD, {"id": id}))
        if not out_rows:
            return None
        node = client.node_to_dict(out_rows[0][0])
        node.pop("embedding", None)
        outgoing = [e for e in (out_rows[0][1] or []) if e.get("id")]
        in_rows = _rows(client.ro_query(Q.INCOMING, {"id": id}))
        incoming = [e for e in (in_rows[0][0] or []) if e.get("id")] if in_rows else []
        return {"node": node, "edges": outgoing + incoming}
