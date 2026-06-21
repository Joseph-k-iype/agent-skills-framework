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
            "overall_score": self.overall_score,
            "summary": self.summary,
        }
