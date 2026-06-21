import json
import tempfile
from pathlib import Path

from skill_sdk.evaluation.memory import (
    feedback_path,
    load_feedback,
    load_memory_context,
    record_feedback,
)


def test_load_feedback_returns_empty_when_missing():
    tmp = Path(tempfile.mkdtemp())
    data = load_feedback(tmp, "demo-skill")
    assert data == {"skill_name": "demo-skill", "entries": []}


def test_record_feedback_persists_atomically():
    tmp = Path(tempfile.mkdtemp())
    entry = record_feedback(
        tmp, "demo-skill",
        finding_id="f1",
        finding_signature="description:missing-invocation-trigger",
        finding_text="description doesn't say when to invoke",
        verdict="dismissed",
        run_id="run-1",
    )
    assert entry["verdict"] == "dismissed"
    path = feedback_path(tmp, "demo-skill")
    assert path.exists()
    on_disk = json.loads(path.read_text())
    assert on_disk["entries"][0]["finding_signature"] == "description:missing-invocation-trigger"
    # no leftover temp files
    assert list(path.parent.glob(".*.tmp")) == []


def test_record_feedback_appends_across_calls():
    tmp = Path(tempfile.mkdtemp())
    record_feedback(tmp, "demo-skill", "f1", "sig-a", "text a", "dismissed")
    record_feedback(tmp, "demo-skill", "f2", "sig-b", "text b", "accepted")
    data = load_feedback(tmp, "demo-skill")
    assert len(data["entries"]) == 2


def test_memory_context_empty_when_no_history():
    tmp = Path(tempfile.mkdtemp())
    assert load_memory_context(tmp, "demo-skill") == ""


def test_memory_context_formats_dismissed_and_accepted():
    tmp = Path(tempfile.mkdtemp())
    record_feedback(tmp, "demo-skill", "f1", "sig-a", "missing invocation trigger", "dismissed")
    record_feedback(tmp, "demo-skill", "f2", "sig-b", "body restates frontmatter", "accepted")
    context = load_memory_context(tmp, "demo-skill")
    assert "DISMISSED: missing invocation trigger" in context
    assert "ACCEPTED: body restates frontmatter" in context


def test_memory_context_keeps_only_latest_verdict_per_signature():
    tmp = Path(tempfile.mkdtemp())
    record_feedback(tmp, "demo-skill", "f1", "sig-a", "same finding", "dismissed", run_id="run-1")
    record_feedback(tmp, "demo-skill", "f1b", "sig-a", "same finding", "accepted", run_id="run-2")
    context = load_memory_context(tmp, "demo-skill")
    assert context.count("same finding") == 1
    assert "ACCEPTED: same finding" in context
    assert "DISMISSED: same finding" not in context


def test_feedback_is_per_skill_name_not_per_version():
    tmp = Path(tempfile.mkdtemp())
    record_feedback(tmp, "demo-skill", "f1", "sig-a", "text", "dismissed")
    # No version parameter anywhere in the API — confirms the file is keyed
    # purely by skill name so dismissals survive version bumps.
    path = feedback_path(tmp, "demo-skill")
    assert path.name == "demo-skill.json"
    assert path.parent.name == "_feedback"


def test_load_feedback_tolerates_corrupt_file():
    tmp = Path(tempfile.mkdtemp())
    path = feedback_path(tmp, "demo-skill")
    path.parent.mkdir(parents=True)
    path.write_text("not json{{{")
    assert load_feedback(tmp, "demo-skill") == {"skill_name": "demo-skill", "entries": []}
