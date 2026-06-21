import json
import tempfile
from pathlib import Path

from skill_sdk.evaluation.executor import execute_case

MANIFEST = {
    "name": "demo-skill",
    "version": "1.0.0",
    "description": "A demo skill",
    "runtime": "python",
    "api_version": 1,
    "entry": "src/main.py",
}

SKILL_SOURCE = """
from skill_sdk import BaseSkill, SkillResult


class DemoSkill(BaseSkill):
    name = "demo-skill"
    version = "1.0.0"

    async def initialize(self, ctx):
        pass

    async def handle_command(self, command):
        if command.name == "discover":
            return SkillResult(status="success", data={"columns": ["id", "email"]})
        return SkillResult(status="error", error="unknown command")

    async def handle_event(self, event):
        return SkillResult(status="success", data={"event": event.name})

    async def health_check(self):
        from skill_sdk import HealthStatus
        return HealthStatus(healthy=True)

    async def shutdown(self):
        pass
"""


def _make_skill(tmp: Path) -> Path:
    src = tmp / "src"
    src.mkdir(parents=True)
    (src / "main.py").write_text(SKILL_SOURCE)
    (tmp / "skill.json").write_text(json.dumps(MANIFEST))
    return tmp


def test_exact_match_passes_on_specified_subset_of_fields():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    case = {
        "id": "discover-basic",
        "input": {"type": "command", "name": "discover", "args": []},
        "expect": {"mode": "exact_match", "value": {"status": "success"}},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "passed"
    assert outcome["actual"]["columns"] == ["id", "email"]


def test_exact_match_fails_when_field_differs():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    case = {
        "id": "discover-wrong",
        "input": {"type": "command", "name": "discover", "args": []},
        "expect": {"mode": "exact_match", "value": {"status": "error"}},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "failed"


def test_contains_passes_on_substring_in_list():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    case = {
        "id": "discover-contains",
        "input": {"type": "command", "name": "discover", "args": []},
        "expect": {"mode": "contains", "value": {"columns": "email"}},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "passed"


def test_llm_judged_returns_pending_judgment_with_rubric():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    case = {
        "id": "discover-judged",
        "input": {"type": "command", "name": "discover", "args": []},
        "expect": {"mode": "llm_judged", "rubric": "score it", "value": None},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "pending_judgment"
    assert outcome["rubric"] == "score it"
    assert outcome["actual"]["columns"] == ["id", "email"]


def test_event_input_runs_through_handle_event():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    case = {
        "id": "event-case",
        "input": {"type": "event", "name": "tick", "payload": {}},
        "expect": {"mode": "exact_match", "value": {"event": "tick"}},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "passed"


def test_unknown_command_surfaces_as_failed_not_error():
    tmp = _make_skill(Path(tempfile.mkdtemp()))
    case = {
        "id": "bad-command",
        "input": {"type": "command", "name": "nonexistent", "args": []},
        "expect": {"mode": "exact_match", "value": {"status": "success"}},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "failed"
    assert outcome["actual"]["status"] == "error"


def test_missing_skill_surfaces_as_error_not_exception():
    tmp = Path(tempfile.mkdtemp())
    case = {
        "id": "no-skill",
        "input": {"type": "command", "name": "discover", "args": []},
        "expect": {"mode": "exact_match", "value": {"status": "success"}},
    }
    outcome = execute_case(tmp, case)
    assert outcome["status"] == "error"
    assert "detail" in outcome
