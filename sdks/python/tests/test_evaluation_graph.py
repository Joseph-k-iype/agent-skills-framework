import json
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage

import skill_sdk.evaluation.graph as graph_mod
from skill_sdk.evaluation import evaluate_skill

from _fake_chat_model import FakeToolCallingChatModel

MANIFEST = {
    "name": "demo-skill",
    "version": "1.0.0",
    "description": "A demo skill",
    "runtime": "python",
    "api_version": 1,
    "entry": "src/main.py",
}

SKILL_SOURCE = """
from skill_sdk import BaseSkill, SkillResult, HealthStatus


class DemoSkill(BaseSkill):
    name = "demo-skill"
    version = "1.0.0"

    async def initialize(self, ctx):
        pass

    async def handle_command(self, command):
        return SkillResult(status="success", data={"echo": command.name})

    async def handle_event(self, event):
        return SkillResult(status="success", data={})

    async def health_check(self):
        return HealthStatus(healthy=True)

    async def shutdown(self):
        pass
"""

CASES_YAML = """
version: 1
cases:
  - id: deterministic-case
    description: exact_match, scored without any model
    input: {type: command, name: noop, args: []}
    expect: {mode: exact_match, value: {status: success}}
  - id: judged-case
    description: scored by the content/test agents
    input: {type: command, name: noop, args: []}
    expect: {mode: llm_judged, rubric: "always pass", value: null}
"""


def _make_skill(tmp: Path) -> Path:
    src = tmp / "src"
    src.mkdir(parents=True)
    (src / "main.py").write_text(SKILL_SOURCE)
    (tmp / "skill.json").write_text(json.dumps(MANIFEST))
    (tmp / "tests").mkdir()
    (tmp / "tests" / "eval_cases.yaml").write_text(CASES_YAML)
    return tmp


def test_graph_skips_judging_when_no_model_available(monkeypatch):
    monkeypatch.setattr(graph_mod, "_build_model", lambda: None)
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    report = evaluate_skill(tmp, registry_path=tmp / "registry")

    assert report.judge_status == "skipped"
    assert report.test_executor.passed == 1  # deterministic case still runs
    assert report.test_executor.total == 2
    skipped = [r for r in report.test_executor.results if r["case_id"] == "judged-case"]
    assert skipped[0]["status"] == "skipped"


def test_graph_runs_full_agentic_pass_with_fake_model(monkeypatch):
    fake_model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "read_skill_md", "args": {}, "id": "c1"}]),
        AIMessage(content=json.dumps({"findings": []})),
        AIMessage(content="", tool_calls=[{
            "name": "score_rubric",
            "args": {"case_id": "judged-case", "rubric": "always pass", "raw_output": "echo: noop", "score": 95, "rationale": "matches"},
            "id": "c2",
        }]),
        AIMessage(content=json.dumps({
            "judgments": [{"case_id": "judged-case", "score": 95, "passed": True, "rationale": "matches"}]
        })),
    ])
    monkeypatch.setattr(graph_mod, "_build_model", lambda: fake_model)

    tmp = _make_skill(Path(tempfile.mkdtemp()))
    report = evaluate_skill(tmp, registry_path=tmp / "registry")

    assert report.judge_status == "ok"
    assert report.content_critic_findings == []
    assert report.test_executor.passed == 2
    assert report.test_executor.failed == 0
    assert report.overall_score == 100.0


def test_graph_degrades_to_error_status_when_agent_invocation_raises(monkeypatch):
    class ExplodingModel:
        def bind_tools(self, *a, **k):
            return self

    monkeypatch.setattr(graph_mod, "_build_model", lambda: ExplodingModel())

    tmp = _make_skill(Path(tempfile.mkdtemp()))
    report = evaluate_skill(tmp, registry_path=tmp / "registry")

    assert report.judge_status == "error"
    assert report.judge_skip_reason is not None
    # deterministic results already collected before the agentic pass survive
    assert any(r["case_id"] == "deterministic-case" for r in report.test_executor.results)
