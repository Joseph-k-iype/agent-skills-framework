"""Governance evaluator — required frontmatter, naming conventions, policy."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.okf.concept import Concept

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class GovernanceEvaluator(Evaluator):
    name = "governance"

    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        findings: list[EvalFinding] = []

        # OKF requires a `type`. parse_concept defaults it, so check the raw fm.
        if not concept.frontmatter.get("type"):
            findings.append(
                EvalFinding(
                    severity="error",
                    message="Missing required frontmatter field: type",
                    evidence=None,
                )
            )

        # Filename should be kebab-case.
        stem = PurePosixPath(concept.path).stem
        if not _KEBAB.match(stem):
            findings.append(
                EvalFinding(
                    severity="warning", message="Filename is not kebab-case", evidence=stem
                )
            )

        if not concept.title:
            findings.append(
                EvalFinding(severity="warning", message="Missing title", evidence=None)
            )
        if not concept.tags:
            findings.append(
                EvalFinding(severity="info", message="No tags for discoverability", evidence=None)
            )

        blocking = any(f.severity == "error" for f in findings)
        penalty = sum(
            {"error": 40.0, "warning": 12.0, "info": 4.0}[f.severity] for f in findings
        )
        score = max(0.0, 100.0 - penalty)
        return EvalResult(self.name, score, findings, blocking=blocking)
