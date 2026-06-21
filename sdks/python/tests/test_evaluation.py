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


def test_evaluate_skill_reports_structural_errors():
    tmp = Path(tempfile.mkdtemp())
    bad_manifest = dict(MANIFEST)
    del bad_manifest["description"]
    _make_skill(tmp, bad_manifest)
    report = evaluate_skill(tmp)
    assert any("description" in e.lower() for e in report.structural_errors)


def test_evaluate_skill_never_raises_without_eval_extras_installed():
    tmp = Path(tempfile.mkdtemp())
    _make_skill(tmp)
    # No SKILLS_EVAL_MODEL / langchain installed in the base test env — must
    # degrade gracefully rather than raising ImportError.
    report = evaluate_skill(tmp)
    assert report.judge_status in ("skipped", "error")
