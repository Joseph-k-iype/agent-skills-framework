from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from ..validation import find_manifest_file
from .cases import load_eval_cases
from .executor import _repo_root, execute_case


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def make_read_skill_md_tool(skill_path: str | Path):
    skill_path = Path(skill_path)

    @tool
    def read_skill_md() -> str:
        """Read this skill's manifest file (SKILL.md/skill.yaml/skill.json) verbatim,
        including the YAML frontmatter and the Markdown body."""
        manifest_path = find_manifest_file(skill_path)
        if manifest_path is None:
            return "ERROR: no manifest file found"
        return _read_text(manifest_path)

    return read_skill_md


def make_read_reference_examples_tool(exclude_name: str | None = None, limit: int = 3):
    repo_root = _repo_root()

    @tool
    def read_reference_examples(skill_names: list[str] | None = None) -> str:
        """Read up to 3 other skills' SKILL.md files in this repo as exemplars of
        good description/body style. Pass specific skill_names to target particular
        skills, or omit to get a default sample."""
        skills_dir = repo_root / "skills"
        if not skills_dir.exists():
            return "No reference skills directory found."
        candidates = skill_names or [
            p.name
            for p in sorted(skills_dir.iterdir())
            if p.is_dir() and p.name != exclude_name
        ][:limit]
        out = []
        for name in candidates:
            manifest_path = find_manifest_file(skills_dir / name)
            if manifest_path is None:
                continue
            out.append(f"=== {name} ===\n{_read_text(manifest_path)}")
        return "\n\n".join(out) if out else "No reference skills found."

    return read_reference_examples


def make_run_test_case_tool(skill_path: str | Path):
    skill_path = Path(skill_path)

    @tool
    def run_test_case(case_id: str) -> dict[str, Any]:
        """Execute one declarative eval case (by its id, from this skill's
        tests/eval_cases.yaml) against the real skill and report the raw outcome."""
        cases = {c["id"]: c for c in load_eval_cases(skill_path)}
        case = cases.get(case_id)
        if case is None:
            return {"case_id": case_id, "status": "error", "detail": f"unknown case id '{case_id}'"}
        return execute_case(skill_path, case)

    return run_test_case


def make_score_rubric_tool():
    @tool
    def score_rubric(
        case_id: str, rubric: str, raw_output: str, score: float, rationale: str
    ) -> dict[str, Any]:
        """Record a 0-100 score and rationale for how well raw_output satisfies
        rubric, for the given case_id. Call this once per llm_judged case before
        giving your final answer."""
        return {
            "case_id": case_id,
            "score": score,
            "passed": score >= 60,
            "rationale": rationale,
        }

    return score_rubric
