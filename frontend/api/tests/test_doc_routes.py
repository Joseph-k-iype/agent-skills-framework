from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import deps
from api.main import app


@pytest.fixture
def client(monkeypatch):
    registry_dir = Path(tempfile.mkdtemp()) / "registry"
    workspace_dir = Path(tempfile.mkdtemp()) / "workspace"
    monkeypatch.setattr(deps, "_registry_path", registry_dir)
    monkeypatch.setattr(deps, "_registry_client", None)
    monkeypatch.setenv("SKILLS_WORKSPACE", str(workspace_dir))
    monkeypatch.delenv("SKILLS_API_KEY", raising=False)
    return TestClient(app)


def _manifest(name="doc-skill", version="1.0.0", body=None):
    m = {
        "name": name,
        "version": version,
        "description": "a demo skill for doc tests",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
        "capabilities": ["demo:run"],
        "permissions": [{"resource": "db", "actions": ["read"]}],
    }
    if body is not None:
        m["body"] = body
    return m


def _publish(client, **kw):
    r = client.post("/api/skills/scaffold", json={"manifest": _manifest(**kw), "publish": True})
    assert r.status_code == 200, r.text
    assert r.json()["success"] is True


class TestUpdateDoc:
    def test_update_body_and_preserve_frontmatter(self, client):
        _publish(client, body="# doc-skill\n\nOriginal body.")

        new_body = "# Title\n\n**Bold** and a diagram:\n\n```mermaid\ngraph TD\nA-->B\n```"
        r = client.put("/api/skills/doc-skill/doc", json={"body": new_body})
        assert r.status_code == 200, r.text
        assert r.json()["body"] == new_body.strip()

        # body is updated; frontmatter fields survive
        manifest = client.get("/api/skills/doc-skill/manifest").json()
        assert manifest["body"].strip() == new_body.strip()
        assert manifest["manifest"]["name"] == "doc-skill"
        assert manifest["manifest"]["version"] == "1.0.0"
        assert manifest["manifest"]["runtime"] == "python"
        assert "```mermaid" in manifest["raw"]

    def test_id_unchanged_after_doc_edit(self, client):
        """The body is not hashed, so editing it must leave verify() valid."""
        _publish(client, body="# doc-skill\n\nOriginal.")
        before = client.get("/api/skills/doc-skill").json()["ids"]["1.0.0"]

        r = client.put("/api/skills/doc-skill/doc", json={"body": "# totally different docs"})
        assert r.status_code == 200, r.text

        verify = client.post("/api/skills/doc-skill/verify").json()
        assert verify["valid"] is True, verify
        after = client.get("/api/skills/doc-skill").json()["ids"]["1.0.0"]
        assert before == after

    def test_audit_records_doc_update(self, client):
        _publish(client, body="# x")
        client.put("/api/skills/doc-skill/doc", json={"body": "# y"})
        actions = [e["action"] for e in client.get("/api/audit").json()["entries"]]
        assert "Skill Docs Updated" in actions

    def test_unknown_skill_404(self, client):
        r = client.put("/api/skills/no-such-skill/doc", json={"body": "x"})
        assert r.status_code == 404

    def test_legacy_manifest_rejected(self, client):
        _publish(client, body="# x")
        # Swap the served SKILL.md for a legacy manifest name.
        rel = client.get("/api/skills/doc-skill").json()["locations"]["local"]
        skill_dir = deps._registry_path / rel
        (skill_dir / "SKILL.md").rename(skill_dir / "skill.yaml")

        r = client.put("/api/skills/doc-skill/doc", json={"body": "x"})
        assert r.status_code == 400
        assert "SKILL.md" in r.json()["detail"]

    def test_api_key_gate(self, client, monkeypatch):
        _publish(client, body="# x")
        monkeypatch.setenv("SKILLS_API_KEY", "secret-key")
        r = client.put("/api/skills/doc-skill/doc", json={"body": "# y"})
        assert r.status_code == 401
        r2 = client.put(
            "/api/skills/doc-skill/doc",
            json={"body": "# y"},
            headers={"X-API-Key": "secret-key"},
        )
        assert r2.status_code == 200
