import json
import tempfile
from pathlib import Path

from _fake_chat_model import FakeToolCallingChatModel
from langchain_core.messages import AIMessage

from skill_sdk.evaluation.baseline import find_previous_version, run_agent_execution

MANIFEST = {"name": "demo", "version": "1.1.0",
            "permissions": [{"resource": "ws", "actions": ["read", "write", "create", "list"]}]}


def _skill(tmp: Path, body: str = "Write out.txt with the answer.") -> Path:
    (tmp / "SKILL.md").write_text(f"---\nname: demo\nversion: 1.1.0\n---\n{body}")
    return tmp


def test_find_previous_version_picks_semver_max_below_current():
    reg = Path(tempfile.mkdtemp())
    skills = reg / "skills"
    for v in ("0.9.0", "1.0.0", "1.0.5", "1.1.0"):
        (skills / f"demo-{v}").mkdir(parents=True)
    prev = find_previous_version(reg, "demo", "1.1.0")
    assert prev is not None and prev.name == "demo-1.0.5"


def test_run_agent_execution_with_without_computes_delta():
    skill = _skill(Path(tempfile.mkdtemp()))
    reg = Path(tempfile.mkdtemp())  # no prior version -> with_without
    case = {"id": "c1", "input": {"type": "task", "prompt": "produce out.txt"},
            "expect": {"mode": "assertions",
                       "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}

    # with-skill writes the file (passes); baseline does nothing (fails)
    def fresh_model():
        return FakeToolCallingChatModel(responses=[
            AIMessage(content="", tool_calls=[
                {"name": "write_file", "args": {"path": "out.txt", "content": "x"}, "id": "1"}]),
            AIMessage(content="done"),
            AIMessage(content="I won't do it"),  # baseline run: no tool call
        ])

    summary = run_agent_execution(skill, MANIFEST, reg, [case], fresh_model())
    assert summary.comparison_mode == "with_without"
    assert summary.with_skill.pass_rate_mean == 1.0
    assert summary.baseline.pass_rate_mean == 0.0
    assert summary.delta["pass_rate"] == 1.0


def test_judge_run_parses_rubric_and_llm_assertions():
    from skill_sdk.evaluation.baseline import judge_run
    from skill_sdk.evaluation.trajectory import RunResult
    model = FakeToolCallingChatModel(responses=[AIMessage(content=json.dumps({
        "llm_assertions": [{"statement": "clean", "passed": True, "evidence": "tidy"}],
        "rubric_score": 80,
    }))])
    case = {"expect": {"assertions": [{"kind": "llm", "statement": "clean"}],
                       "rubric": "is it clean?"}}
    out = judge_run(model, case, RunResult(final_text="ok"))
    assert out["rubric_score"] == 80
    assert out["llm_assertions"][0]["passed"] is True
