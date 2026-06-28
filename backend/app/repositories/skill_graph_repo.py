"""FalkorDB persistence for Skill nodes, references, capabilities, versions."""

from __future__ import annotations

from typing import Any

from app.graph import client
from app.graph.cypher import skill as Q


def _rows(result) -> list[list[Any]]:
    return result.result_set or []


def _skill(node) -> dict:
    d = client.node_to_dict(node)
    d.pop("embedding", None)
    return d


class SkillGraphRepository:
    def create_skill(
        self,
        *,
        id: str,
        skill_key: str,
        name: str,
        description: str | None,
        runtime: str,
        version: str,
        workspace_id: str | None,
        folder_id: str,
        tags: list[str],
        capabilities: list[str],
        ts: str,
    ) -> dict | None:
        rows = _rows(
            client.query(
                Q.CREATE_SKILL,
                {
                    "id": id,
                    "skill_key": skill_key,
                    "name": name,
                    "description": description,
                    "runtime": runtime,
                    "version": version,
                    "workspace_id": workspace_id,
                    "folder_id": folder_id,
                    "tags": tags,
                    "capabilities": capabilities,
                    "ts": ts,
                },
            )
        )
        return _skill(rows[0][0]) if rows else None

    def get_skill(self, id: str) -> dict | None:
        rows = _rows(client.ro_query(Q.GET_SKILL, {"id": id}))
        if not rows:
            return None
        d = _skill(rows[0][0])
        d["references"] = [r for r in (rows[0][1] or []) if r.get("id")]
        d["capabilities"] = [c for c in (rows[0][2] or []) if c]
        return d

    def list_current(
        self, *, workspace_id: str | None, folder_id: str | None, q: str | None, limit: int = 100
    ) -> list[dict]:
        rows = _rows(
            client.ro_query(
                Q.LIST_CURRENT,
                {"workspace_id": workspace_id, "folder_id": folder_id, "q": q, "limit": limit},
            )
        )
        return [_skill(r[0]) for r in rows]

    def update_skill(
        self,
        *,
        id: str,
        name: str | None,
        description: str | None,
        runtime: str | None,
        tags: list[str] | None,
        capabilities: list[str] | None,
        ts: str,
    ) -> dict | None:
        rows = _rows(
            client.query(
                Q.UPDATE_SKILL,
                {
                    "id": id,
                    "name": name,
                    "description": description,
                    "runtime": runtime,
                    "tags": tags,
                    "capabilities": capabilities,
                    "ts": ts,
                },
            )
        )
        return _skill(rows[0][0]) if rows else None

    def set_status(self, *, id: str, status: str, ts: str) -> dict | None:
        rows = _rows(client.query(Q.SET_STATUS, {"id": id, "status": status, "ts": ts}))
        return _skill(rows[0][0]) if rows else None

    def delete_skill(self, id: str) -> None:
        client.query(Q.DELETE_SKILL, {"id": id})

    # references / capabilities
    def set_references(self, *, id: str, doc_ids: list[str]) -> None:
        client.query(Q.CLEAR_REFERENCES, {"id": id})
        for doc_id in doc_ids:
            client.query(Q.ADD_REFERENCE, {"id": id, "doc_id": doc_id})

    def set_capabilities(self, *, id: str, names: list[str], ts: str) -> None:
        client.query(Q.CLEAR_CAPABILITIES, {"id": id})
        for name in names:
            client.query(Q.ADD_CAPABILITY, {"id": id, "name": name, "ts": ts})

    # versioning
    def create_version(self, *, old_id: str, new_id: str, version: str, skill_key: str, ts: str) -> dict | None:
        client.query(Q.CLEAR_CURRENT, {"skill_key": skill_key})
        rows = _rows(
            client.query(Q.CREATE_VERSION, {"old_id": old_id, "id": new_id, "version": version, "ts": ts})
        )
        client.query(Q.COPY_EDGES, {"old_id": old_id, "new_id": new_id})
        return _skill(rows[0][0]) if rows else None

    def version_chain(self, skill_key: str) -> list[dict]:
        rows = _rows(client.ro_query(Q.VERSION_CHAIN, {"skill_key": skill_key}))
        return [_skill(r[0]) for r in rows]

    def clone_skill(
        self, *, src_id: str, new_id: str, skill_key: str, name: str, folder_id: str, ts: str
    ) -> dict | None:
        rows = _rows(
            client.query(
                Q.CLONE_SKILL,
                {
                    "src_id": src_id,
                    "id": new_id,
                    "skill_key": skill_key,
                    "name": name,
                    "folder_id": folder_id,
                    "ts": ts,
                },
            )
        )
        return _skill(rows[0][0]) if rows else None
