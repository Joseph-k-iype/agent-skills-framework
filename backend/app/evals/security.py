"""Security evaluator — secret scanning and unsafe-prompt heuristics."""

from __future__ import annotations

import re

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.okf.concept import Concept

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS secret access key", re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*\S+")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Generic API key", re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    ("Hardcoded password", re.compile(r"(?i)\bpassword\s*[:=]\s*['\"]?\S{4,}")),
    ("Bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.]{20,}")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}")),
]

_UNSAFE_PROMPTS = [
    "ignore previous instructions",
    "disregard all prior",
    "ignore all previous",
    "reveal your system prompt",
]


class SecurityEvaluator(Evaluator):
    name = "security"

    def run_rules(self, concept: Concept, bundle_files: list[str]) -> EvalResult:
        findings: list[EvalFinding] = []
        text = concept.body
        for label, pattern in _SECRET_PATTERNS:
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                redacted = snippet[:6] + "…" if len(snippet) > 6 else snippet
                findings.append(
                    EvalFinding(
                        severity="error",
                        message=f"Possible {label} in body",
                        evidence=redacted,
                    )
                )
        lowered = text.lower()
        for phrase in _UNSAFE_PROMPTS:
            if phrase in lowered:
                findings.append(
                    EvalFinding(
                        severity="warning",
                        message="Prompt-injection style phrase detected",
                        evidence=phrase,
                    )
                )
        blocking = any(f.severity == "error" for f in findings)
        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        score = max(0.0, 100.0 - 50.0 * errors - 10.0 * warnings)
        return EvalResult(self.name, score, findings, blocking=blocking)
