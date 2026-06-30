"""Quality evaluator — completeness rules + optional LLM correctness judgment."""

from __future__ import annotations

import re

from app.evals.agent import EvalAgent
from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.llm.provider import LLMProvider
from app.okf.concept import Concept

_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)
_CODE_FENCE = re.compile(r"```")


class QualityEvaluator(Evaluator):
    name = "quality"

    def __init__(self, agent: EvalAgent | None = None) -> None:
        self._agent = agent or EvalAgent()

    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        findings: list[EvalFinding] = []
        body = concept.body

        if not _HEADING.search(body):
            findings.append(
                EvalFinding(severity="warning", message="No section headings", evidence=None)
            )
        if not _CODE_FENCE.search(body):
            findings.append(
                EvalFinding(severity="info", message="No examples / code blocks", evidence=None)
            )
        if len(body.strip()) < 40:
            findings.append(
                EvalFinding(severity="warning", message="Body is very thin", evidence=None)
            )
        if not concept.description:
            findings.append(
                EvalFinding(severity="info", message="No description for previews", evidence=None)
            )

        penalty = sum({"error": 30.0, "warning": 18.0, "info": 6.0}[f.severity] for f in findings)
        score = max(0.0, 100.0 - penalty)
        return EvalResult(self.name, score, findings, blocking=False)

    async def run_llm_judge(
        self, concept: Concept, provider: LLMProvider
    ) -> EvalResult | None:
        # `provider` decides whether base.evaluate calls us at all; the actual
        # model call goes through the Pydantic AI agent (structured + retries).
        if not self._agent.available:
            return None
        quality = await self._agent.quality_score(concept)
        if quality is None:
            return None
        return EvalResult(
            self.name,
            float(quality.score),
            [
                EvalFinding(
                    severity="info",
                    message="LLM quality judgment",
                    evidence=quality.justification[:280],
                )
            ],
            blocking=False,
            used_llm=True,
        )
