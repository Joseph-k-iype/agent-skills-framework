from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .validation import load_manifest


GRAPH_QUERIES = {
    "create_skill_node": """
MERGE (s:Skill {name: $name})
ON CREATE SET s.description = $description, s.runtime = $runtime, s.created_at = timestamp()
""",
    "create_version_node": """
MERGE (sv:SkillVersion {id: $id})
ON CREATE SET sv.name = $name, sv.version = $version, sv.entry = $entry, sv.created_at = timestamp()
""",
    "link_version_to_skill": """
MATCH (s:Skill {name: $name}), (sv:SkillVersion {id: $id})
MERGE (sv)-[:VERSION_OF]->(s)
""",
    "link_capability": """
MATCH (sv:SkillVersion {id: $id})
MERGE (c:Capability {name: $capability})
MERGE (sv)-[:PROVIDES]->(c)
""",
    "link_dependency": """
MATCH (a:SkillVersion {id: $a_id})
MERGE (b:Skill {name: $dep_name})
MERGE (a)-[:DEPENDS_ON]->(b)
""",
    "link_permission": """
MATCH (sv:SkillVersion {id: $id})
MERGE (p:Permission {resource: $resource})
MERGE (sv)-[r:REQUESTS]->(p)
ON CREATE SET r.actions = $actions
""",
    "register_deployment": """
MATCH (sv:SkillVersion {id: $skill_id})
MERGE (d:Deployment {id: $deployment_id})
ON CREATE SET d.platform = $platform, d.environment = $environment, d.status = $status, d.deployed_at = timestamp()
MERGE (sv)-[:DEPLOYED_AT]->(d)
""",
    "find_impact": """
MATCH (sv:SkillVersion {id: $id})-[:DEPENDS_ON*]->(dep:Skill)
OPTIONAL MATCH (dep)<-[:DEPENDS_ON]-(upstream:SkillVersion)
RETURN sv, dep, upstream
""",
    "find_skill_by_capability": """
MATCH (c:Capability {name: $capability})<-[:PROVIDES]-(sv:SkillVersion)-[:VERSION_OF]->(s:Skill)
RETURN s.name, sv.version, sv.id
""",
    "find_skill_by_permission": """
MATCH (p:Permission {resource: $resource})<-[:REQUESTS]-(sv:SkillVersion)-[:VERSION_OF]->(s:Skill)
RETURN s.name, sv.version, p.resource
""",
    "get_dependency_chain": """
MATCH path = (sv:SkillVersion {id: $id})-[:DEPENDS_ON*]->(dep:Skill)
RETURN path
""",
    "list_deployments": """
MATCH (sv:SkillVersion {id: $id})-[:DEPLOYED_AT]->(d:Deployment)
RETURN d.platform, d.environment, d.status, d.deployed_at
""",
}


class FalkorDBConnector:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        graph_name: str = "agent-skills",
        username: str | None = None,
        password: str | None = None,
        ssl: bool = False,
        enabled: bool = True,
    ):
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self.username = username
        self.password = password
        self.ssl = ssl
        self.enabled = enabled
        self._graph = None
        self._connection = None

    @property
    def connected(self) -> bool:
        return self._connection is not None

    async def connect(self) -> bool:
        if not self.enabled:
            return False
        try:
            import redis
            url = f"redis://{self.host}:{self.port}"
            if self.username and self.password:
                url = f"redis://{self.username}:{self.password}@{self.host}:{self.port}"
            if self.ssl:
                url = url.replace("redis://", "rediss://")
            self._connection = redis.from_url(url, decode_responses=True)
            self._connection.ping()
            self._graph = self._connection.graph(self.graph_name)
            return True
        except ImportError:
            return False
        except Exception:
            self._connection = None
            self._graph = None
            return False

    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
            self._graph = None

    @property
    def graph(self):
        if not self._graph:
            raise RuntimeError("FalkorDB not connected — call connect() first")
        return self._graph

    def query(self, query: str, params: dict[str, Any] | None = None) -> list[Any]:
        if not self._graph:
            return []
        try:
            result = self.graph.query(query, params or {})
            return result.result_set
        except Exception:
            return []

    def register_skill(self, manifest_path: str | Path) -> dict[str, Any]:
        if not self._graph:
            return {"status": "skipped", "reason": "not connected"}

        manifest = load_manifest(manifest_path)
        skill_id = manifest.get("id", "")
        name = manifest["name"]
        version = manifest["version"]

        try:
            self.graph.query(GRAPH_QUERIES["create_skill_node"], {
                "name": name,
                "description": manifest.get("description", ""),
                "runtime": manifest.get("runtime", ""),
            })
            self.graph.query(GRAPH_QUERIES["create_version_node"], {
                "id": skill_id,
                "name": name,
                "version": version,
                "entry": manifest.get("entry", ""),
            })
            self.graph.query(GRAPH_QUERIES["link_version_to_skill"], {
                "name": name,
                "id": skill_id,
            })
            for cap in manifest.get("capabilities", []):
                self.graph.query(GRAPH_QUERIES["link_capability"], {
                    "id": skill_id,
                    "capability": cap,
                })
            for dep in manifest.get("dependencies", {}).get("skills", []):
                parts = dep.split("@")
                dep_name = parts[0]
                self.graph.query(GRAPH_QUERIES["link_dependency"], {
                    "a_id": skill_id,
                    "dep_name": dep_name,
                })
            for perm in manifest.get("permissions", []):
                self.graph.query(GRAPH_QUERIES["link_permission"], {
                    "id": skill_id,
                    "resource": perm.get("resource", ""),
                    "actions": perm.get("actions", []),
                })
            return {"status": "registered", "id": skill_id, "name": name, "version": version}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def find_impact(self, skill_id: str) -> list[dict[str, Any]]:
        results = self.query(GRAPH_QUERIES["find_impact"], {"id": skill_id})
        impacted = []
        for row in results:
            impacted.append({
                "skill": str(row[0]),
                "dependency": str(row[1]) if len(row) > 1 else "",
                "upstream": str(row[2]) if len(row) > 2 else "",
            })
        return impacted

    def find_skills_by_capability(self, capability: str) -> list[dict[str, Any]]:
        results = self.query(GRAPH_QUERIES["find_skill_by_capability"], {"capability": capability})
        skills = []
        for row in results:
            skills.append({
                "name": row[0],
                "version": row[1],
                "id": row[2],
            })
        return skills

    def find_skills_by_permission(self, resource: str) -> list[dict[str, Any]]:
        results = self.query(GRAPH_QUERIES["find_skill_by_permission"], {"resource": resource})
        skills = []
        for row in results:
            skills.append({
                "name": row[0],
                "version": row[1],
                "resource": row[2],
            })
        return skills

    def register_deployment(
        self,
        skill_id: str,
        deployment_id: str,
        platform: str,
        environment: str,
        status: str = "active",
    ) -> dict[str, Any]:
        if not self._graph:
            return {"status": "skipped", "reason": "not connected"}
        try:
            self.graph.query(GRAPH_QUERIES["register_deployment"], {
                "skill_id": skill_id,
                "deployment_id": deployment_id,
                "platform": platform,
                "environment": environment,
                "status": status,
            })
            return {"status": "registered", "deployment_id": deployment_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
