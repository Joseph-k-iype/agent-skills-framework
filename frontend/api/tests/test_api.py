from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import deps
from api.main import app


@pytest.fixture
def client(monkeypatch):
    """A TestClient backed by an isolated temp registry + workspace."""
    registry_dir = Path(tempfile.mkdtemp()) / "registry"
    workspace_dir = Path(tempfile.mkdtemp()) / "workspace"
    monkeypatch.setattr(deps, "_registry_path", registry_dir)
    monkeypatch.setattr(deps, "_registry_client", None)
    monkeypatch.setenv("SKILLS_WORKSPACE", str(workspace_dir))
    monkeypatch.delenv("SKILLS_API_KEY", raising=False)
    return TestClient(app)


def _manifest(name="demo-skill", version="1.0.0"):
    return {
        "name": name,
        "version": version,
        "description": "a demo skill for tests",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
        "capabilities": ["demo:run"],
        "permissions": [{"resource": "db", "actions": ["read"]}],
    }


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_empty_registry(client):
    assert client.get("/api/skills").json() == {}
    info = client.get("/api/registry").json()
    assert info["skill_count"] == 0
    assert info["auth_required"] is False
    assert "workspace" in info


class TestPathSafety:
    def test_build_rejects_traversal(self, client):
        r = client.post("/api/skills/build", json={"path": "../../../etc"})
        assert r.status_code == 400
        assert "escape" in r.json()["detail"].lower()

    def test_publish_rejects_absolute_outside(self, client):
        r = client.post("/api/skills/publish", json={"path": "/etc"})
        assert r.status_code == 400

    def test_scaffold_rejects_entry_traversal(self, client, tmp_path):
        """Bug #1: the `entry` field must be sandboxed like `files` keys are."""
        canary = tmp_path / "pwned_entry.py"
        manifest = _manifest(name="evil-skill")
        manifest["entry"] = f"../../../../../..{canary}"
        r = client.post("/api/skills/scaffold", json={"manifest": manifest})
        assert r.status_code == 400
        assert "escape" in r.json()["detail"].lower()
        assert not canary.exists()

    def test_resolve_in_workspace_rejects_nul_byte(self, client):
        """Bug #2: an embedded NUL byte must 400, not crash with ValueError/500."""
        r = client.post("/api/skills/build", json={"path": "foo\x00bar"})
        assert r.status_code == 400


class TestScaffoldPublishInstall:
    def test_full_lifecycle(self, client):
        # scaffold + publish
        r = client.post("/api/skills/scaffold", json={"manifest": _manifest(), "publish": True})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["published"]["version"] == "1.0.0"

        # appears in listing + compliance
        assert "demo-skill" in client.get("/api/skills").json()
        comp = client.get("/api/skills/compliance").json()["skills"]
        row = next(s for s in comp if s["name"] == "demo-skill")
        assert row["valid"] is True
        assert row["runtime"] == "python"
        assert row["permissions"] == 1
        assert row["permission_details"] == [{"resource": "db", "actions": ["read"]}]

        # install into the workspace sandbox
        ri = client.post("/api/skills/demo-skill/install", json={"verify": True})
        assert ri.status_code == 200, ri.text
        installed = ri.json()["path"]
        assert "workspace" in installed

        # audit recorded the operations (newest first)
        actions = [e["action"] for e in client.get("/api/audit").json()["entries"]]
        assert "Skill Installed" in actions
        assert "Skill Published" in actions
        assert "Skill Scaffolded" in actions

    def test_scaffold_invalid_name_reports_errors(self, client):
        r = client.post("/api/skills/scaffold", json={"manifest": _manifest(name="Invalid_Name")})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is False
        assert body["errors"]

    def test_scaffold_concurrent_without_force_one_wins(self, client, monkeypatch):
        """Bug #4: the exists()-then-mkdir() TOCTOU window must be closed.

        Simulate the race by making the directory appear only *after* the
        route's exists()-style check would have run, then asserting that the
        authoritative mkdir(exist_ok=False) still raises 400 instead of two
        concurrent callers both writing into the same directory.
        """
        r1 = client.post("/api/skills/scaffold", json={"manifest": _manifest(name="race-skill")})
        assert r1.status_code == 200
        r2 = client.post("/api/skills/scaffold", json={"manifest": _manifest(name="race-skill")})
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"].lower()

    def test_scaffold_force_overwrites_without_race_error(self, client):
        r1 = client.post("/api/skills/scaffold", json={"manifest": _manifest(name="force-skill")})
        assert r1.status_code == 200
        r2 = client.post("/api/skills/scaffold", json={"manifest": _manifest(name="force-skill"), "force": True})
        assert r2.status_code == 200


class TestAuditResilience:
    def test_audit_write_failure_does_not_fail_operation(self, client, monkeypatch):
        """Bug #3: a broken audit log must not turn a successful op into a 500."""
        from api import audit as audit_module

        def boom(*args, **kwargs):
            raise OSError("disk full (simulated)")

        monkeypatch.setattr(audit_module, "_audit_path", boom)
        r = client.post("/api/skills/scaffold", json={"manifest": _manifest(name="audit-fail-skill")})
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True


class TestCompliancePermissionsTypeGuard:
    def test_non_list_permissions_does_not_corrupt_count(self, client, monkeypatch):
        """Bug #5: a truthy non-list `permissions` must not produce len() of a string."""
        from skill_sdk import validation as validation_module

        manifest = _manifest(name="bad-perms-skill")
        manifest["permissions"] = [{"resource": "db", "actions": ["read"]}]
        r = client.post("/api/skills/scaffold", json={"manifest": manifest, "publish": True})
        assert r.status_code == 200, r.text

        original_load_manifest = validation_module.load_manifest

        def patched_load_manifest(path):
            m = dict(original_load_manifest(path))
            if m.get("name") == "bad-perms-skill":
                m["permissions"] = "not-a-list"
            return m

        import api.routes.skills as skills_module
        monkeypatch.setattr(skills_module, "load_manifest", patched_load_manifest)

        comp = client.get("/api/skills/compliance").json()["skills"]
        row = next(s for s in comp if s["name"] == "bad-perms-skill")
        assert row["permissions"] == 0
        assert row["permission_details"] == []


class TestImpact:
    def test_downstream_impact(self, client):
        client.post("/api/skills/scaffold", json={"manifest": _manifest(name="base-skill"), "publish": True})
        dependent = _manifest(name="dependent-skill")
        dependent["dependencies"] = {"skills": ["base-skill@^1.0.0"]}
        client.post("/api/skills/scaffold", json={"manifest": dependent, "publish": True})

        impact = client.get("/api/skills/base-skill/impact").json()
        assert impact == {"downstream": ["dependent-skill"], "count": 1}

        leaf_impact = client.get("/api/skills/dependent-skill/impact").json()
        assert leaf_impact == {"downstream": [], "count": 0}

    def test_impact_unknown_skill_404s(self, client):
        r = client.get("/api/skills/no-such-skill/impact")
        assert r.status_code == 404


class TestVersionsSorted:
    def test_semver_order(self, client):
        for v in ("0.9.0", "0.10.0", "0.2.0"):
            client.post("/api/skills/scaffold", json={"manifest": _manifest(version=v), "publish": True, "force": True})
        vers = client.get("/api/skills/demo-skill/versions").json()
        # Ascending SemVer order — lexical sort would put 0.10.0 before 0.2.0/0.9.0.
        assert vers["versions"] == ["0.2.0", "0.9.0", "0.10.0"]
        assert vers["latest"] == "0.10.0"


class TestDeployments:
    def test_local_registry_target_present(self, client):
        client.post("/api/skills/scaffold", json={"manifest": _manifest(), "publish": True})
        d = client.get("/api/deployments").json()
        names = [t["name"] for t in d["targets"]]
        assert "Local Registry" in names
        assert d["total_skills"] == 1


class TestApiKeyGate:
    def test_mutation_blocked_without_key(self, client, monkeypatch):
        monkeypatch.setenv("SKILLS_API_KEY", "secret-key")
        # No key header → 401 on a mutating endpoint.
        r = client.post("/api/skills/scaffold", json={"manifest": _manifest()})
        assert r.status_code == 401
        # Correct key → allowed.
        r2 = client.post(
            "/api/skills/scaffold",
            json={"manifest": _manifest()},
            headers={"X-API-Key": "secret-key"},
        )
        assert r2.status_code == 200

    def test_reads_open_even_with_key(self, client, monkeypatch):
        monkeypatch.setenv("SKILLS_API_KEY", "secret-key")
        assert client.get("/api/skills").status_code == 200
