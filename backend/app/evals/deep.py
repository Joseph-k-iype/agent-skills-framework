"""Agentic deep evaluation — LLM-as-judge skill effectiveness.

Distinct from the six fast rule-based evaluators. On demand, an LLM:

1. generates N realistic test cases + edge cases for the skill,
2. answers each case **without** the skill (a plain assistant baseline),
3. answers each case **with** the skill body provided as instructions,
4. judges both answers and scores them 0-10.

The headline metric is *effectiveness* — does the skill improve answers vs. no
skill (per-case delta + win-rate). Requires a chat-capable provider; with the
local/offline provider it returns a clear "unavailable" report.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from app.core.logging import get_logger
from app.llm.provider import LLMProvider, get_provider
from app.okf.concept import Concept

log = get_logger("evals.deep")

_GEN_SYSTEM = (
    "You generate evaluation test cases for an AI skill. Given the skill, produce "
    "realistic tasks a user might ask, including tricky edge cases. Return ONLY a JSON "
    'array of objects: [{"scenario": "<a concrete task/input>", "edge_case": true|false}]. '
    "No prose."
)

_PLAIN_SYSTEM = "You are a helpful assistant. Complete the user's task as well as you can."

_JUDGE_SYSTEM = (
    "You are an impartial judge. You are given a task and two candidate answers: "
    "answer A was produced WITHOUT a specialist skill, answer B WITH it. Score each "
    "0-10 for correctness and usefulness. Return ONLY a JSON object: "
    '{"without_score": <0-10>, "with_score": <0-10>, "note": "<one short sentence>"}.'
)


def _skill_system(concept: Concept) -> str:
    return (
        "You are an assistant equipped with the following skill. Apply it to answer the "
        f"user's task.\n\n# Skill: {concept.title}\n{concept.body}"
    )


def _judge_user(scenario: str, without: str, with_: str) -> str:
    return (
        f"TASK:\n{scenario}\n\n"
        f"ANSWER A (without skill):\n{without}\n\n"
        f"ANSWER B (with skill):\n{with_}"
    )


def _extract_json(text: str, opener: str, closer: str):
    start = text.find(opener)
    end = text.rfind(closer)
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON found")
    return json.loads(text[start : end + 1])


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
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_provider()

    async def evaluate(self, concept: Concept, n_cases: int = 5) -> DeepEvalReport:
        if not self.provider.has_chat:
            return DeepEvalReport(
                available=False,
                reason=(
                    "Deep evaluation needs a chat-capable LLM provider. Set "
                    "settings.llm_provider (anthropic/openai/openrouter) and a key."
                ),
                summary="Unavailable — no chat-capable provider configured.",
            )

        cases = await self._generate_cases(concept, n_cases)
        results: list[DeepCase] = []
        skipped = 0
        for spec in cases:
            scenario = str(spec.get("scenario", "")).strip()
            if not scenario:
                continue
            without = await self.provider.chat(_PLAIN_SYSTEM, scenario)
            with_ = await self.provider.chat(_skill_system(concept), scenario)
            # A failed/rate-limited call returns None — don't score it 0 (that
            # would falsely look like a regression). Skip and report it instead.
            if without is None or with_ is None:
                skipped += 1
                continue
            verdict = self._parse_verdict(
                await self.provider.chat(_JUDGE_SYSTEM, _judge_user(scenario, without, with_))
            )
            if verdict is None:
                skipped += 1
                continue
            with_score, without_score, note = verdict
            results.append(
                DeepCase(
                    scenario=scenario,
                    is_edge_case=bool(spec.get("edge_case", False)),
                    with_score=with_score,
                    without_score=without_score,
                    delta=round(with_score - without_score, 2),
                    note=note,
                )
            )

        return self._aggregate(results, skipped)

    async def _generate_cases(self, concept: Concept, n_cases: int) -> list[dict]:
        prompt = (
            f"Skill title: {concept.title}\nSkill type: {concept.type}\n\n"
            f"{concept.body}\n\nGenerate exactly {n_cases} test cases."
        )
        raw = await self.provider.chat(_GEN_SYSTEM, prompt)
        try:
            data = _extract_json(raw or "", "[", "]")
            return [d for d in data if isinstance(d, dict)][:n_cases]
        except Exception as exc:
            log.warning("deep_eval_case_parse_failed", error=str(exc))
            return []

    def _parse_verdict(self, raw: str | None) -> tuple[float, float, str | None] | None:
        try:
            obj = _extract_json(raw or "", "{", "}")
            with_score = float(obj.get("with_score", 0))
            without_score = float(obj.get("without_score", 0))
            return with_score, without_score, obj.get("note")
        except Exception:
            return None

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
