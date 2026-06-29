"""Eval supervisor — runs the six evaluators and aggregates a report.

Runs every evaluator concurrently. Each evaluator is hybrid (rules always, LLM
when the provider supports chat), so the supervisor works fully offline and
lights up richer judgment purely by configuration.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field

from app.evals.base import EvalResult, Evaluator
from app.evals.cost import CostEvaluator
from app.evals.documentation import DocumentationEvaluator
from app.evals.governance import GovernanceEvaluator
from app.evals.performance import PerformanceEvaluator
from app.evals.quality import QualityEvaluator
from app.evals.security import SecurityEvaluator
from app.llm.provider import get_provider
from app.okf.concept import Concept


def _default_evaluators() -> list[Evaluator]:
    return [
        SecurityEvaluator(),
        DocumentationEvaluator(),
        GovernanceEvaluator(),
        CostEvaluator(),
        PerformanceEvaluator(),
        QualityEvaluator(),
    ]


@dataclass
class EvalReport:
    overall_score: float
    confidence: float
    passed: bool  # no blocking issues
    results: list[EvalResult] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    used_llm: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class EvalSupervisor:
    def __init__(self, evaluators: list[Evaluator] | None = None) -> None:
        self.evaluators = evaluators if evaluators is not None else _default_evaluators()
        self.provider = get_provider()

    async def evaluate(self, concept: Concept, bundle_files: list[str]) -> EvalReport:
        results: list[EvalResult] = await asyncio.gather(
            *(e.evaluate(concept, self.provider, bundle_files) for e in self.evaluators)
        )

        overall = round(sum(r.score for r in results) / len(results), 1) if results else 0.0
        used_llm = any(r.used_llm for r in results)
        # Confidence rises when model judgment backs the rule-based scores.
        llm_fraction = sum(1 for r in results if r.used_llm) / len(results) if results else 0.0
        confidence = round(0.6 + 0.4 * llm_fraction, 2)

        blocking_issues: list[str] = []
        recommendations: list[str] = []
        for r in results:
            for f in r.findings:
                if r.blocking and f.severity == "error":
                    blocking_issues.append(f"[{r.evaluator}] {f.message}")
                elif f.severity in ("warning", "error"):
                    recommendations.append(f"[{r.evaluator}] {f.message}")

        return EvalReport(
            overall_score=overall,
            confidence=confidence,
            passed=not blocking_issues,
            results=results,
            blocking_issues=blocking_issues,
            recommendations=recommendations,
            used_llm=used_llm,
        )
