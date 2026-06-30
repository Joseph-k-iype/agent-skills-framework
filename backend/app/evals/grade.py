"""Interactive evaluation — grade a skill's output against user-provided expectations.

Distinct from deep eval (with/without lift): here the user supplies test cases as
``{input, expected}`` and we measure correctness. For each case the skill runs on
the input, then an LLM judge scores the actual output against the expected one
(0-10 + pass/fail + reasoning). Headline metrics are pass-rate and average score.
Reuses the Pydantic AI :class:`app.evals.agent.EvalAgent` (structured + retries).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.evals.agent import EvalAgent
from app.okf.concept import Concept


@dataclass
class GradeCaseResult:
    input: str
    expected: str
    actual: str
    score: float
    passed: bool
    reasoning: str | None = None


@dataclass
class GradeReport:
    available: bool
    reason: str | None = None
    cases: list[GradeCaseResult] = field(default_factory=list)
    skipped: int = 0  # provider errors / rate limits
    missing_expected: int = 0  # cases left blank by the user — can't be graded
    pass_rate: float = 0.0
    avg_score: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class GradeEvaluator:
    def __init__(self, agent: EvalAgent | None = None) -> None:
        self.agent = agent or EvalAgent()

    async def evaluate(self, concept: Concept, cases: list[dict]) -> GradeReport:
        if not self.agent.available:
            return GradeReport(
                available=False,
                reason=(
                    "Interactive evaluation needs a chat-capable LLM provider. Set an "
                    "OpenRouter API key (settings.openrouter_api_key) to enable it."
                ),
                summary="Unavailable — no chat-capable provider configured.",
            )

        results: list[GradeCaseResult] = []
        skipped = 0
        missing_expected = 0
        for case in cases:
            inp = str(case.get("input", "")).strip()
            expected = str(case.get("expected", "")).strip()
            if not inp:
                continue
            if not expected:
                # Nothing to grade against — surfaced to the user to fill in.
                missing_expected += 1
                continue
            actual = await self.agent.answer_with_skill(concept, inp)
            if actual is None:
                skipped += 1
                continue
            verdict = await self.agent.grade(input=inp, expected=expected, actual=actual)
            if verdict is None:
                skipped += 1
                continue
            results.append(
                GradeCaseResult(
                    input=inp,
                    expected=expected,
                    actual=actual,
                    score=verdict.score,
                    passed=verdict.passed,
                    reasoning=verdict.reasoning,
                )
            )

        return self._aggregate(results, skipped, missing_expected)

    def _aggregate(
        self, cases: list[GradeCaseResult], skipped: int, missing_expected: int
    ) -> GradeReport:
        notes = []
        if skipped:
            notes.append(f"{skipped} skipped (provider errors / rate limits)")
        if missing_expected:
            notes.append(f"{missing_expected} missing an expected output")
        note = f" ({'; '.join(notes)})" if notes else ""

        if not cases:
            return GradeReport(
                available=True,
                cases=[],
                skipped=skipped,
                missing_expected=missing_expected,
                summary=f"No cases graded.{note}",
            )
        n = len(cases)
        passed = sum(1 for c in cases if c.passed)
        pass_rate = round(passed / n, 2)
        avg_score = round(sum(c.score for c in cases) / n, 2)
        summary = (
            f"Passed {passed}/{n} ({round(pass_rate * 100)}%), "
            f"avg score {avg_score}/10{note}."
        )
        return GradeReport(
            available=True,
            cases=cases,
            skipped=skipped,
            missing_expected=missing_expected,
            pass_rate=pass_rate,
            avg_score=avg_score,
            summary=summary,
        )
