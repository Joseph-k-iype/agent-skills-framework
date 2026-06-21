from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from ..validation import find_manifest_file, lint_full_skill, load_manifest, validate_full_skill
from .cases import load_eval_cases
from .executor import execute_case
from .state import EvaluationReport, ExecutorSummary

__all__ = ["evaluate_skill", "EvaluationReport", "ExecutorSummary"]


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _run_deterministic_cases(
    skill_path: Path, eval_cases: list[dict[str, Any]], report: EvaluationReport
) -> list[dict[str, Any]]:
    """Run every non-llm_judged case in plain code (no model required) and fold
    the results into ``report.test_executor``. Returns the llm_judged cases'
    pending-judgment results, left for the agentic pass (if any) to score."""
    pending_judgment = []
    for case in eval_cases:
        outcome = execute_case(skill_path, case)
        if outcome["status"] == "pending_judgment":
            pending_judgment.append(outcome)
            continue
        report.test_executor.results.append(outcome)
        if outcome["status"] == "passed":
            report.test_executor.passed += 1
        elif outcome["status"] in ("failed", "error"):
            report.test_executor.failed += 1
    return pending_judgment


def _mark_pending_skipped(report: EvaluationReport, pending_judgment: list[dict[str, Any]]) -> None:
    """llm_judged cases with no judge available are neither pass nor fail —
    they're simply unscored. Surfaced in results as 'skipped' rather than
    silently dropped or, worse, counted as failures."""
    for outcome in pending_judgment:
        report.test_executor.results.append({**outcome, "status": "skipped"})


def evaluate_skill(
    skill_path: str | Path,
    judge: str | None = None,
    registry_path: str | Path | None = None,
) -> EvaluationReport:
    """Run the evaluation framework against a skill directory.

    Structural validation/lint and deterministic (exact_match/contains) test
    cases always run — zero model, zero optional dependencies required. The
    content-critic and test-executor agent passes (``skill_sdk.evaluation.graph``)
    are layered on top, scoring only the llm_judged cases, when a chat model is
    configured; absent that — or with ``judge="none"`` — this degrades to
    ``judge_status="skipped"`` with structural + deterministic results only.
    Never raises for a missing/misconfigured judge.
    """
    skill_path = Path(skill_path).resolve()
    registry_path = Path(registry_path).resolve() if registry_path else Path.cwd() / "registry"
    manifest_path = find_manifest_file(skill_path)
    manifest: dict[str, Any] = {}
    if manifest_path is not None:
        try:
            manifest = load_manifest(manifest_path)
        except Exception:
            manifest = {}

    structural_errors = validate_full_skill(skill_path)
    structural_warnings = lint_full_skill(skill_path)

    try:
        eval_cases = load_eval_cases(skill_path)
    except ValueError as e:
        structural_warnings.append(str(e))
        eval_cases = []

    report = EvaluationReport(
        skill_name=manifest.get("name", skill_path.name),
        skill_version=manifest.get("version", "0.0.0"),
        run_at=_now_iso(),
        judge_status="skipped",
        judge_skip_reason=None,
        structural_errors=structural_errors,
        structural_warnings=structural_warnings,
        test_executor=ExecutorSummary(total=len(eval_cases)),
    )

    pending_judgment = _run_deterministic_cases(skill_path, eval_cases, report)

    if judge == "none":
        report.judge_skip_reason = "judge explicitly disabled (--judge none)"
        _mark_pending_skipped(report, pending_judgment)
        report.summary = _summarize(report)
        return report

    try:
        from .graph import run_agentic_evaluation
    except ImportError:
        report.judge_skip_reason = "evaluation agents unavailable (install skill_sdk[eval])"
        _mark_pending_skipped(report, pending_judgment)
        report.summary = _summarize(report)
        return report

    return run_agentic_evaluation(
        skill_path=skill_path,
        manifest=manifest,
        registry_path=registry_path,
        pending_judgment=pending_judgment,
        base_report=report,
        judge=judge,
    )


def _summarize(report: EvaluationReport) -> str:
    if report.structural_errors:
        return (
            f"{len(report.structural_errors)} structural error(s); "
            f"content/test judging {report.judge_status}."
        )
    return f"Structural checks passed; content/test judging {report.judge_status}."
