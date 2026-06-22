from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

JudgeStatus = Literal["ok", "skipped", "error"]


class EvaluationState(TypedDict, total=False):
    skill_path: str
    skill_name: str
    skill_version: str
    registry_path: str
    manifest: dict[str, Any]
    eval_cases: list[dict[str, Any]]
    memory_context: str
    model: Any  # live BaseChatModel instance — graph-invocation-only, never serialized/reported
    pending_judgment: list[dict[str, Any]]
    structural_errors: list[str]
    structural_warnings: list[str]
    content_critic_findings: list[dict[str, Any]]
    content_critic_model: str | None
    test_executor_results: list[dict[str, Any]]
    judge_status: JudgeStatus
    judge_skip_reason: str | None
    report: dict[str, Any]


@dataclass
class ExecutorSummary:
    results: list[dict[str, Any]] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    total: int = 0


@dataclass
class ConfigAggregate:
    pass_rate_mean: float = 0.0
    pass_rate_stddev: float = 0.0
    tokens_mean: float = 0.0
    tokens_stddev: float = 0.0
    duration_mean: float = 0.0
    duration_stddev: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate_mean": self.pass_rate_mean,
            "pass_rate_stddev": self.pass_rate_stddev,
            "tokens_mean": self.tokens_mean,
            "tokens_stddev": self.tokens_stddev,
            "duration_mean": self.duration_mean,
            "duration_stddev": self.duration_stddev,
        }


@dataclass
class AgentExecutionSummary:
    comparison_mode: str  # "with_without" | "vs_previous" | "skipped"
    skip_reason: str | None
    runs_per_case: int
    with_skill: ConfigAggregate = field(default_factory=ConfigAggregate)
    baseline: ConfigAggregate = field(default_factory=ConfigAggregate)
    delta: dict[str, Any] = field(default_factory=dict)
    cases: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_mode": self.comparison_mode,
            "skip_reason": self.skip_reason,
            "runs_per_case": self.runs_per_case,
            "with_skill": self.with_skill.to_dict(),
            "baseline": self.baseline.to_dict(),
            "delta": self.delta,
            "cases": self.cases,
        }


@dataclass
class EvaluationReport:
    skill_name: str
    skill_version: str
    run_at: str
    judge_status: JudgeStatus
    judge_skip_reason: str | None
    structural_errors: list[str] = field(default_factory=list)
    structural_warnings: list[str] = field(default_factory=list)
    content_critic_findings: list[dict[str, Any]] = field(default_factory=list)
    content_critic_model: str | None = None
    test_executor: ExecutorSummary = field(default_factory=ExecutorSummary)
    agent_execution: AgentExecutionSummary | None = None
    overall_score: float | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "run_at": self.run_at,
            "judge_status": self.judge_status,
            "judge_skip_reason": self.judge_skip_reason,
            "structural_errors": self.structural_errors,
            "structural_warnings": self.structural_warnings,
            "content_critic": {
                "findings": self.content_critic_findings,
                "model": self.content_critic_model,
            },
            "test_executor": {
                "results": self.test_executor.results,
                "passed": self.test_executor.passed,
                "failed": self.test_executor.failed,
                "total": self.test_executor.total,
            },
            "agent_execution": self.agent_execution.to_dict() if self.agent_execution else None,
            "overall_score": self.overall_score,
            "summary": self.summary,
        }


_SEVERITY_WEIGHT = {"error": 20, "warning": 10, "info": 2}


def compute_overall_score(report: EvaluationReport) -> float | None:
    components: list[float] = []
    te = report.test_executor
    if te.total:
        components.append(100.0 * te.passed / te.total)
    if report.judge_status == "ok":
        # The content critic ran (regardless of whether it found anything) —
        # a clean run earns full marks here, same as the original graph
        # scorer. Gating on findings being non-empty (instead of on the
        # critic having run) would silently exclude this component, and
        # therefore lower the overall score, for ordinary successful runs.
        penalty = sum(_SEVERITY_WEIGHT.get(f.get("severity", "info"), 2)
                      for f in report.content_critic_findings)
        components.append(max(0.0, 100.0 - penalty))
    ae = report.agent_execution
    if ae and ae.comparison_mode != "skipped":
        components.append(100.0 * ae.with_skill.pass_rate_mean)
    return round(sum(components) / len(components), 2) if components else None
