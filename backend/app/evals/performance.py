"""Performance evaluator — structural complexity heuristics."""

from __future__ import annotations

import re

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.okf.concept import Concept

_HEADING = re.compile(r"^(#{1,6})\s", re.MULTILINE)
_MAX_DEPTH = 4
_LONG_BODY_LINES = 400


class PerformanceEvaluator(Evaluator):
    name = "performance"

    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        findings: list[EvalFinding] = []
        lines = concept.body.count("\n") + 1
        depths = [len(m.group(1)) for m in _HEADING.finditer(concept.body)]
        max_depth = max(depths) if depths else 0

        if lines > _LONG_BODY_LINES:
            findings.append(
                EvalFinding(
                    severity="warning",
                    message="Very long body — consider splitting into linked concepts",
                    evidence=f"{lines} lines",
                )
            )
        if max_depth > _MAX_DEPTH:
            findings.append(
                EvalFinding(
                    severity="info",
                    message="Deep heading nesting may hurt readability",
                    evidence=f"depth {max_depth}",
                )
            )

        penalty = sum({"error": 30.0, "warning": 15.0, "info": 5.0}[f.severity] for f in findings)
        score = max(0.0, 100.0 - penalty)
        return EvalResult(self.name, score, findings, blocking=False)
