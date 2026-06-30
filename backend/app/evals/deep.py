"""Agentic deep evaluation — LLM-as-judge skill effectiveness.

Distinct from the six fast rule-based evaluators. On demand, an LLM:

1. generates N realistic test cases + edge cases for the skill,
2. answers each case **without** the skill (a plain assistant baseline),
3. answers each case **with** the skill body provided as instructions,
4. judges both answers and scores them 0-10.

The headline metric is *effectiveness* — does the skill improve answers vs. no
skill (per-case delta + win-rate). Uses a Pydantic AI agent (:mod:`app.evals.agent`)
for validated structured output and transient-error retries; with no chat-capable
provider it returns a clear "unavailable" report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.evals.agent import EvalAgent
from app.okf.concept import Concept


@dataclass
class DeepCase:
    scenario: str
    is_edge_case: bool
    with_score: float
    without_score: float
    delta: float
    note: str | None = None


@dataclass
class DeepEvalReport:
    available: bool
    reason: str | None = None
    cases: list[DeepCase] = field(default_factory=list)
    skipped: int = 0  # cases dropped due to provider errors / rate limits
    effectiveness_avg: float = 0.0  # avg(with - without)
    win_rate: float = 0.0  # fraction of cases where with > without
    with_avg: float = 0.0
    without_avg: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class DeepEvaluator:
    def __init__(self, agent: EvalAgent | None = None) -> None:
        self.agent = agent or EvalAgent()

    async def evaluate(self, concept: Concept, n_cases: int = 5) -> DeepEvalReport:
        if not self.agent.available:
            return DeepEvalReport(
                available=False,
                reason=(
                    "Deep evaluation needs a chat-capable LLM provider. Set an "
                    "OpenRouter API key (settings.openrouter_api_key) to enable it."
                ),
                summary="Unavailable — no chat-capable provider configured.",
            )

        cases = await self.agent.generate_cases(concept, n_cases)
        results: list[DeepCase] = []
        skipped = 0
        for spec in cases:
            scenario = spec.scenario.strip()
            if not scenario:
                continue
            without = await self.agent.answer_plain(scenario)
            with_ = await self.agent.answer_with_skill(concept, scenario)
            # A failed/rate-limited call returns None — don't score it 0 (that
            # would falsely look like a regression). Skip and report it instead.
            if without is None or with_ is None:
                skipped += 1
                continue
            verdict = await self.agent.judge(scenario, without, with_)
            if verdict is None:
                skipped += 1
                continue
            results.append(
                DeepCase(
                    scenario=scenario,
                    is_edge_case=spec.edge_case,
                    with_score=verdict.with_score,
                    without_score=verdict.without_score,
                    delta=round(verdict.with_score - verdict.without_score, 2),
                    note=verdict.note,
                )
            )

        return self._aggregate(results, skipped)

    def _aggregate(self, cases: list[DeepCase], skipped: int = 0) -> DeepEvalReport:
        if not cases:
            note = (
                f" ({skipped} case(s) skipped due to provider errors / rate limits)"
                if skipped
                else ""
            )
            return DeepEvalReport(
                available=True,
                skipped=skipped,
                cases=[],
                summary=f"No usable test cases completed.{note}",
            )
        n = len(cases)
        with_avg = round(sum(c.with_score for c in cases) / n, 2)
        without_avg = round(sum(c.without_score for c in cases) / n, 2)
        eff = round(sum(c.delta for c in cases) / n, 2)
        wins = sum(1 for c in cases if c.with_score > c.without_score)
        win_rate = round(wins / n, 2)
        if eff > 0.5:
            verdict = "improves"
        elif eff >= -0.5:
            verdict = "no clear improvement on"
        else:
            verdict = "regresses"
        skip_note = f" ({skipped} skipped due to rate limits)" if skipped else ""
        summary = (
            f"The skill {verdict} answers: {eff:+} avg over {n} scored case(s), "
            f"winning {wins}/{n} (with {with_avg} vs without {without_avg}){skip_note}."
        )
        return DeepEvalReport(
            available=True,
            cases=cases,
            skipped=skipped,
            effectiveness_avg=eff,
            win_rate=win_rate,
            with_avg=with_avg,
            without_avg=without_avg,
            summary=summary,
        )
