"""Quality evaluator — completeness rules + optional LLM correctness judgment."""

from __future__ import annotations

import re

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.llm.provider import LLMProvider
from app.okf.concept import Concept

_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)
_CODE_FENCE = re.compile(r"```")

_JUDGE_SYSTEM = (
    "You are a senior reviewer scoring an OKF knowledge concept for correctness and "
    "completeness. Reply with a single integer 0-100 (higher is better) on the first line, "
    "then one short sentence of justification."
)


class QualityEvaluator(Evaluator):
    name = "quality"

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
        prompt = f"Title: {concept.title}\nType: {concept.type}\n\n{concept.body}"
        reply = await provider.chat(_JUDGE_SYSTEM, prompt)
        if not reply:
            return None
        first = reply.strip().splitlines()[0]
        digits = re.search(r"\d{1,3}", first)
        score = float(min(100, int(digits.group(0)))) if digits else 70.0
        justification = reply.strip()[:280]
        return EvalResult(
            self.name,
            score,
            [EvalFinding(severity="info", message="LLM quality judgment", evidence=justification)],
            blocking=False,
            used_llm=True,
        )
