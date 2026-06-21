from __future__ import annotations

import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["accepted", "dismissed"]

FEEDBACK_DIRNAME = "_feedback"


def feedback_path(registry_path: str | Path, skill_name: str) -> Path:
    return Path(registry_path) / "skills" / FEEDBACK_DIRNAME / f"{skill_name}.json"


def load_feedback(registry_path: str | Path, skill_name: str) -> dict[str, Any]:
    path = feedback_path(registry_path, skill_name)
    if not path.exists():
        return {"skill_name": skill_name, "entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"skill_name": skill_name, "entries": []}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return {"skill_name": skill_name, "entries": []}
    return data


def record_feedback(
    registry_path: str | Path,
    skill_name: str,
    finding_id: str,
    finding_signature: str,
    finding_text: str,
    verdict: Verdict,
    run_id: str | None = None,
    verdict_by: str | None = None,
) -> dict[str, Any]:
    """Append a human accept/dismiss verdict for a finding.

    Written directly with an atomic ``os.replace`` swap — independent
    per-skill files under low contention, so this intentionally does not
    take the registry's ``fcntl`` index lock (that guards ``index.yaml``
    mutations only; see ``RegistryClient._locked``).
    """
    data = load_feedback(registry_path, skill_name)
    entry = {
        "finding_id": finding_id,
        "finding_signature": finding_signature,
        "finding_text": finding_text,
        "verdict": verdict,
        "verdict_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "verdict_by": verdict_by,
        "run_id": run_id,
    }
    data["entries"].append(entry)

    path = feedback_path(registry_path, skill_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{skill_name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return entry


def load_memory_context(registry_path: str | Path, skill_name: str) -> str:
    """Format prior accept/dismiss verdicts as few-shot lines for the content
    critic's system prompt, so dismissed findings converge instead of
    recurring every run. Returns "" when there's no feedback history yet.
    """
    data = load_feedback(registry_path, skill_name)
    entries = data.get("entries", [])
    if not entries:
        return ""

    # Keep only the latest verdict per signature — a finding may be dismissed
    # then later re-accepted (or vice versa) as the skill evolves.
    latest: dict[str, dict[str, Any]] = {}
    for entry in entries:
        latest[entry["finding_signature"]] = entry

    lines = [
        "Prior human review of this skill's findings (do not re-flag DISMISSED "
        "items unless the underlying content has materially changed):"
    ]
    for entry in latest.values():
        label = "DISMISSED" if entry["verdict"] == "dismissed" else "ACCEPTED"
        lines.append(f"- {label}: {entry['finding_text']}")
    return "\n".join(lines)
