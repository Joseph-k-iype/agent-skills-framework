import json
import tempfile
from pathlib import Path

from skill_sdk.evaluation import evaluate_skill

MANIFEST = {
    "name": "demo-skill",
    "version": "1.0.0",
    "description": "A demo skill",
    "runtime": "python",
    "api_version": 1,
    "entry": "src/main.py",
}


def _make_skill(tmp: Path, manifest=MANIFEST):
    src = tmp / "src"
    src.mkdir(parents=True)
    (src / "main.py").write_text("# placeholder")
    (tmp / "skill.json").write_text(json.dumps(manifest))


def test_evaluate_skill_skipped_when_no_judge_configured(monkeypatch):
    # _build_model() calls load_dotenv(), which would re-populate
    # SKILLS_EVAL_MODEL from a developer's real repo-root .env even after we
    # delenv it here — stub load_dotenv() itself so this test is deterministic
    # regardless of ambient machine config.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
    tmp = Path(tempfile.mkdtemp())
    _make_skill(tmp)
    report = evaluate_skill(tmp)
    assert report.judge_status == "skipped"
    assert report.structural_errors == []
    assert report.skill_name == "demo-skill"
    assert report.skill_version == "1.0.0"


def test_evaluate_skill_judge_none_forces_skip():
    tmp = Path(tempfile.mkdtemp())
    _make_skill(tmp)
    report = evaluate_skill(tmp, judge="none")
    assert report.judge_status == "skipped"
    assert "disabled" in report.judge_skip_reason


def test_evaluate_skill_reports_structural_errors(monkeypatch):
    # Structural errors don't short-circuit the agentic pass (see evaluate_skill),
    # so this would otherwise also make a real provider call via the ambient
    # repo-root .env — irrelevant to what this test checks, and wasteful/flaky.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
    tmp = Path(tempfile.mkdtemp())
    bad_manifest = dict(MANIFEST)
    del bad_manifest["description"]
    _make_skill(tmp, bad_manifest)
    report = evaluate_skill(tmp)
    assert any("description" in e.lower() for e in report.structural_errors)


def test_evaluate_skill_never_raises_without_eval_extras_installed(monkeypatch):
    # Same ambient-.env hazard as test_evaluate_skill_skipped_when_no_judge_configured:
    # a developer's real repo-root .env can configure SKILLS_EVAL_MODEL, which would
    # make this hit a real provider over the network instead of testing the
    # no-judge-configured degradation path it's named for.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
    tmp = Path(tempfile.mkdtemp())
    _make_skill(tmp)
    # No SKILLS_EVAL_MODEL / langchain installed in the base test env — must
    # degrade gracefully rather than raising ImportError.
    report = evaluate_skill(tmp)
    assert report.judge_status in ("skipped", "error")


def _skill_with_task(tmp: Path):
    (tmp / "src").mkdir(parents=True)
    (tmp / "src" / "main.py").write_text("# placeholder")
    (tmp / "SKILL.md").write_text(
        "---\nname: demo\nversion: 1.0.0\nruntime: python\napi_version: 1\n"
        "entry: src/main.py\ndescription: A demo skill for when you need a demo\n"
        "permissions:\n  - resource: ws\n    actions: [read, write, create, list]\n---\n"
        "Write out.txt containing the answer.")
    (tmp / "tests").mkdir(exist_ok=True)
    (tmp / "tests" / "eval_cases.yaml").write_text(json.dumps({"version": 1, "cases": [
        {"id": "c1", "input": {"type": "task", "prompt": "produce out.txt"},
         "expect": {"mode": "assertions",
                    "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}]}))
    return tmp


def test_evaluate_skill_skips_agent_execution_without_model(monkeypatch):
    monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
    skill = _skill_with_task(Path(tempfile.mkdtemp()))
    report = evaluate_skill(skill, judge="none")
    # judge none -> agent execution skipped, not crashed
    assert report.agent_execution is None or report.agent_execution.comparison_mode == "skipped"
    assert report.judge_status == "skipped"
