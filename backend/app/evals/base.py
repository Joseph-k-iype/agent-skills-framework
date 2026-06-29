"""Evaluator base types — hybrid rules + optional LLM judgment.

Every evaluator runs deterministic ``run_rules`` (always, offline-safe). When the
configured provider supports chat, ``run_llm_judge`` may add a model-based
verdict; its findings and score are merged in. With no chat provider, the result
is purely rules-based — the platform still produces a score offline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.llm.provider import LLMProvider
from app.okf.concept import Concept


@dataclass
class EvalFinding:
    severity: str  # "info" | "warning" | "error"
    message: str
    evidence: str | None = None


@dataclass
class EvalResult:
    evaluator: str
    score: float  # 0..100 (higher is better)
    findings: list[EvalFinding] = field(default_factory=list)
    blocking: bool = False
    used_llm: bool = False


class Evaluator(ABC):
    name: str = "evaluator"

    @abstractmethod
    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        """Deterministic checks. Must never call the network."""

    async def run_llm_judge(
        self, concept: Concept, provider: LLMProvider
    ) -> EvalResult | None:
        """Optional model-based judgment. Default: none."""
        return None

    async def evaluate(
        self, concept: Concept, provider: LLMProvider, bundle_files: list[str]
    ) -> EvalResult:
        base = self.run_rules(concept, bundle_files)
        if not provider.has_chat:
            return base
        judged = await self.run_llm_judge(concept, provider)
        if judged is None:
            return base
        return EvalResult(
            evaluator=self.name,
            # Blend rule and model scores so both matter.
            score=round((base.score + judged.score) / 2, 1),
            findings=base.findings + judged.findings,
            blocking=base.blocking or judged.blocking,
            used_llm=True,
        )
