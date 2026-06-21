from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .state import EvaluationReport

_SEVERITY_WEIGHT = {"error": 20, "warning": 10, "info": 2}


def _build_model() -> Any | None:
    """Construct the configured LangChain chat model, or None if unavailable.

    Mirrors ``FalkorDBConnector.connect()`` in ``graph.py`` at the top level:
    a missing optional package, an unset env var, an unknown provider, or a
    bad key all degrade to None rather than raising — this must never block
    validate/build/publish/CI.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    model_spec = os.environ.get("SKILLS_EVAL_MODEL")
    if not model_spec:
        return None

    try:
        from langchain.chat_models import init_chat_model

        return init_chat_model(model_spec)
    except Exception:
        return None


def _mark_skipped(report: EvaluationReport, pending_judgment: list[dict[str, Any]]) -> None:
    for outcome in pending_judgment:
        report.test_executor.results.append({**outcome, "status": "skipped"})


def _merge_judgments(
    report: EvaluationReport,
    pending_judgment: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
) -> None:
    by_case_id = {j.get("case_id"): j for j in judgments if isinstance(j, dict)}
    for outcome in pending_judgment:
        judgment = by_case_id.get(outcome["case_id"])
        if judgment is None:
            report.test_executor.results.append({**outcome, "status": "skipped"})
            continue
        passed = bool(judgment.get("passed"))
        report.test_executor.results.append({
            **outcome,
            "status": "passed" if passed else "failed",
            "score": judgment.get("score"),
            "rationale": judgment.get("rationale"),
        })
        if passed:
            report.test_executor.passed += 1
        else:
            report.test_executor.failed += 1


def _compute_overall_score(report: EvaluationReport) -> float | None:
    te = report.test_executor
    test_score = 100.0 * te.passed / te.total if te.total else None

    penalty = sum(_SEVERITY_WEIGHT.get(f.get("severity", "info"), 2) for f in report.content_critic_findings)
    content_score = max(0.0, 100.0 - penalty)

    if test_score is None:
        return content_score
    return round((test_score + content_score) / 2, 1)


def run_agentic_evaluation(
    skill_path: str | Path,
    manifest: dict[str, Any],
    registry_path: str | Path,
    pending_judgment: list[dict[str, Any]],
    base_report: EvaluationReport,
) -> EvaluationReport:
    """Layer the content-critic + test-executor agent passes on top of an
    already-structurally-checked report. Any failure here — missing model,
    bad key, provider error mid-run — degrades to judge_status='error' with
    the structural/deterministic results already in base_report left intact;
    it never raises out to the caller.
    """
    report = base_report
    model = _build_model()
    if model is None:
        report.judge_status = "skipped"
        report.judge_skip_reason = "no SKILLS_EVAL_MODEL configured (or model construction failed)"
        _mark_skipped(report, pending_judgment)
        report.summary = _summarize(report)
        return report

    skill_name = manifest.get("name") or Path(skill_path).name

    try:
        from . import memory as memory_mod

        memory_context = memory_mod.load_memory_context(registry_path, skill_name)
    except Exception:
        memory_context = ""

    try:
        from .agents import run_content_critic, run_test_executor

        report.content_critic_findings = run_content_critic(
            model, skill_path, exclude_name=skill_name, memory_context=memory_context
        )
        report.content_critic_model = os.environ.get("SKILLS_EVAL_MODEL")

        judgments = run_test_executor(model, skill_path, pending_judgment)
        _merge_judgments(report, pending_judgment, judgments)

        report.judge_status = "ok"
        report.judge_skip_reason = None
    except Exception as e:
        report.judge_status = "error"
        report.judge_skip_reason = f"{type(e).__name__}: {e}"
        _mark_skipped(report, pending_judgment)

    report.overall_score = _compute_overall_score(report) if report.judge_status == "ok" else report.overall_score
    report.summary = _summarize(report)
    return report


def _summarize(report: EvaluationReport) -> str:
    if report.structural_errors:
        return f"{len(report.structural_errors)} structural error(s); content/test judging {report.judge_status}."
    parts = [f"content/test judging {report.judge_status}"]
    if report.content_critic_findings:
        parts.append(f"{len(report.content_critic_findings)} content finding(s)")
    te = report.test_executor
    if te.total:
        parts.append(f"{te.passed}/{te.total} test cases passed")
    return "Structural checks passed; " + "; ".join(parts) + "."
