from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import deps
from api.main import app
from skill_sdk.evaluation.state import EvaluationReport, ExecutorSummary


@pytest.fixture
def client(monkeypatch):
    registry_dir = Path(tempfile.mkdtemp()) / "registry"
    workspace_dir = Path(tempfile.mkdtemp()) / "workspace"
    monkeypatch.setattr(deps, "_registry_path", registry_dir)
    monkeypatch.setattr(deps, "_registry_client", None)
    monkeypatch.setenv("SKILLS_WORKSPACE", str(workspace_dir))
    monkeypatch.delenv("SKILLS_API_KEY", raising=False)
    return TestClient(app)


def _manifest(name="eval-skill", version="1.0.0"):
    return {
        "name": name,
        "version": version,
        "description": "a demo skill for eval route tests",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
        "capabilities": ["demo:run"],
    }


def _scaffold(client, name="eval-skill", version="1.0.0"):
    r = client.post("/api/skills/scaffold", json={"manifest": _manifest(name, version), "publish": True})
    assert r.status_code == 200, r.text
    return r.json()


def test_cases_round_trip_empty_then_saved(client):
    _scaffold(client)
    r = client.get("/api/skills/eval-skill/evaluation/cases")
    assert r.status_code == 200
    assert r.json() == {"cases": []}

    case = {
        "id": "smoke",
        "description": "basic smoke test",
        "input": {"type": "command", "name": "/x", "args": []},
        "expect": {"mode": "exact_match", "value": {"status": "success"}},
    }
    r = client.put("/api/skills/eval-skill/evaluation/cases", json={"cases": [case]})
    assert r.status_code == 200, r.text
    assert r.json()["cases"] == [case]

    r = client.get("/api/skills/eval-skill/evaluation/cases")
    assert r.json()["cases"] == [case]


def test_cases_rejects_invalid_shape(client):
    _scaffold(client)
    r = client.put("/api/skills/eval-skill/evaluation/cases", json={"cases": [{"id": "bad"}]})
    assert r.status_code == 400


def test_run_evaluation_writes_sidecar_and_updates_compliance(client, monkeypatch):
    _scaffold(client)

    def fake_evaluate_skill(skill_path, judge=None, registry_path=None):
        report = EvaluationReport(
            skill_name="eval-skill",
            skill_version="1.0.0",
            run_at="2026-01-01T00:00:00+00:00",
            judge_status="skipped",
            judge_skip_reason="judge explicitly disabled (--judge none)",
            test_executor=ExecutorSummary(total=0),
        )
        report.overall_score = 87.5
        report.summary = "fake report"
        return report

    monkeypatch.setattr("api.routes.evaluation.evaluate_skill", fake_evaluate_skill)

    r = client.post("/api/skills/eval-skill/evaluation/run", json={"judge": "none"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["judge_status"] == "skipped"
    assert body["overall_score"] == 87.5

    r = client.get("/api/skills/eval-skill/evaluation/latest")
    assert r.status_code == 200
    assert r.json()["overall_score"] == 87.5

    comp = client.get("/api/skills/compliance").json()["skills"]
    row = next(s for s in comp if s["name"] == "eval-skill")
    assert row["last_evaluation_score"] == 87.5


def test_latest_evaluation_404_when_none_run(client):
    _scaffold(client)
    r = client.get("/api/skills/eval-skill/evaluation/latest")
    assert r.status_code == 404


def test_feedback_round_trip(client):
    _scaffold(client)
    r = client.post(
        "/api/skills/eval-skill/evaluation/feedback",
        json={
            "finding_id": "f1",
            "finding_signature": "description:missing-invocation-trigger",
            "finding_text": "description doesn't say when to invoke",
            "verdict": "dismissed",
        },
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/skills/eval-skill/evaluation/feedback")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["verdict"] == "dismissed"


def test_feedback_rejects_bad_verdict(client):
    _scaffold(client)
    r = client.post(
        "/api/skills/eval-skill/evaluation/feedback",
        json={
            "finding_id": "f1",
            "finding_signature": "sig",
            "finding_text": "text",
            "verdict": "maybe",
        },
    )
    assert r.status_code == 400
