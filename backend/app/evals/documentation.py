"""Documentation evaluator — broken links, mermaid syntax, metadata completeness."""

from __future__ import annotations

import re

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.okf.concept import Concept

_FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)


class DocumentationEvaluator(Evaluator):
    name = "documentation"

    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        findings: list[EvalFinding] = []
        bundle = set(bundle_files)

        # Broken internal links — a resolved .md link that isn't in the bundle.
        for link in concept.links:
            if link not in bundle:
                findings.append(
                    EvalFinding(
                        severity="warning", message="Broken internal link", evidence=link
                    )
                )

        # Mermaid fences must be non-empty.
        for lang, content in _FENCE.findall(concept.body):
            if (lang or "").lower() == "mermaid" and not content.strip():
                findings.append(
                    EvalFinding(severity="warning", message="Empty mermaid diagram", evidence=None)
                )

        # Metadata completeness.
        if not concept.description:
            findings.append(
                EvalFinding(severity="info", message="Missing description", evidence=None)
            )
        if not concept.body.strip():
            findings.append(
                EvalFinding(severity="warning", message="Empty body", evidence=None)
            )

        penalty = sum(
            {"error": 30.0, "warning": 12.0, "info": 5.0}[f.severity] for f in findings
        )
        score = max(0.0, 100.0 - penalty)
        return EvalResult(self.name, score, findings, blocking=False)
