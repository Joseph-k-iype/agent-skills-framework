import json
import tempfile
from pathlib import Path

from skill_sdk.evaluation.tools import (
    make_read_skill_md_tool,
    make_read_reference_examples_tool,
    make_run_test_case_tool,
    make_score_rubric_tool,
)

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


def test_read_skill_md_tool_returns_manifest_contents():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    read_skill_md = make_read_skill_md_tool(tmp)
    result = read_skill_md.invoke({})
    assert "demo-skill" in result


def test_read_skill_md_tool_reports_missing_manifest():
    tmp = Path(tempfile.mkdtemp())
    read_skill_md = make_read_skill_md_tool(tmp)
    result = read_skill_md.invoke({})
    assert "ERROR" in result


def test_read_reference_examples_excludes_named_skill():
    read_reference_examples = make_read_reference_examples_tool(exclude_name="data-discovery")
    result = read_reference_examples.invoke({})
    # excluded from the *candidate* skills read (no own section header) — it
    # may still appear as a dependency name inside another skill's manifest
    assert "=== data-discovery ===" not in result


def test_run_test_case_tool_executes_known_case():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    (tmp / "tests").mkdir()
    (tmp / "tests" / "eval_cases.yaml").write_text(
        "version: 1\ncases:\n  - id: c1\n    input: {type: command, name: noop, args: []}\n"
        "    expect: {mode: exact_match, value: {status: success}}\n"
    )
    run_test_case = make_run_test_case_tool(tmp)
    result = run_test_case.invoke({"case_id": "c1"})
    assert result["case_id"] == "c1"
    assert result["status"] == "error"  # placeholder skill has no BaseSkill subclass


def test_run_test_case_tool_unknown_id():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    (tmp / "tests").mkdir()
    (tmp / "tests" / "eval_cases.yaml").write_text("version: 1\ncases: []\n")
    run_test_case = make_run_test_case_tool(tmp)
    result = run_test_case.invoke({"case_id": "nope"})
    assert result["status"] == "error"
    assert "unknown case id" in result["detail"]


def test_score_rubric_tool_marks_passed_threshold():
    score_rubric = make_score_rubric_tool()
    high = score_rubric.invoke(
        {"case_id": "c1", "rubric": "r", "raw_output": "o", "score": 75, "rationale": "good"}
    )
    low = score_rubric.invoke(
        {"case_id": "c1", "rubric": "r", "raw_output": "o", "score": 10, "rationale": "bad"}
    )
    assert high["passed"] is True
    assert low["passed"] is False
