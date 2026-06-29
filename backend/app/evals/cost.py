"""Cost evaluator — rough token-footprint estimate for the concept body."""

from __future__ import annotations

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.okf.concept import Concept

# ~4 characters per token is the common rule-of-thumb for English text.
_CHARS_PER_TOKEN = 4
_WARN_TOKENS = 4000  # very large single concept


class CostEvaluator(Evaluator):
    name = "cost"

    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        tokens = max(1, len(concept.body) // _CHARS_PER_TOKEN)
        findings = [
            EvalFinding(
                severity="info",
                message=f"Estimated ~{tokens} tokens of context",
                evidence=None,
            )
        ]
        if tokens > _WARN_TOKENS:
            findings.append(
                EvalFinding(
                    severity="warning",
                    message="Large concept may be costly to load as context",
                    evidence=f"~{tokens} tokens",
                )
            )
            score = max(40.0, 100.0 - (tokens - _WARN_TOKENS) / 200.0)
        else:
            score = 100.0
        return EvalResult(self.name, round(score, 1), findings, blocking=False)
