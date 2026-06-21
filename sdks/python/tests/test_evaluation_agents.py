import json
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage

from skill_sdk.evaluation.agents import run_content_critic, run_test_executor

from _fake_chat_model import FakeToolCallingChatModel

MANIFEST = {
    "name": "demo-skill",
    "version": "1.0.0",
    "description": "A demo skill",
    "runtime": "python",
    "api_version": 1,
    "entry": "src/main.py",
}


def _make_skill(tmp: Path) -> Path:
    src = tmp / "src"
    src.mkdir(parents=True)
    (src / "main.py").write_text("# placeholder")
    (tmp / "skill.json").write_text(json.dumps(MANIFEST))
    return tmp


def test_run_content_critic_returns_parsed_findings():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "read_skill_md", "args": {}, "id": "1"}]),
        AIMessage(content=json.dumps({
            "findings": [{
                "id": "desc-trigger",
                "severity": "warning",
                "field": "description",
                "message": "missing when-to-use clause",
                "suggestion": "add one",
                "signature": "description:missing-invocation-trigger",
            }]
        })),
    ])
    findings = run_content_critic(model, tmp, exclude_name="demo-skill")
    assert len(findings) == 1
    assert findings[0]["severity"] == "warning"


def test_run_content_critic_tolerates_unparseable_final_answer():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    model = FakeToolCallingChatModel(responses=[AIMessage(content="not json at all")])
    findings = run_content_critic(model, tmp)
    assert findings == []


def test_run_test_executor_returns_empty_when_no_pending_cases():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    model = FakeToolCallingChatModel(responses=[])
    judgments = run_test_executor(model, tmp, [])
    assert judgments == []


def test_run_test_executor_parses_judgments_for_pending_cases():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "score_rubric",
            "args": {"case_id": "c1", "rubric": "r", "raw_output": "o", "score": 90, "rationale": "good"},
            "id": "1",
        }]),
        AIMessage(content=json.dumps({
            "judgments": [{"case_id": "c1", "score": 90, "passed": True, "rationale": "good"}]
        })),
    ])
    pending = [{"case_id": "c1", "mode": "llm_judged", "status": "pending_judgment",
                "actual": {}, "rubric": "r"}]
    judgments = run_test_executor(model, tmp, pending)
    assert judgments == [{"case_id": "c1", "score": 90, "passed": True, "rationale": "good"}]
