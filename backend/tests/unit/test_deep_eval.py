"""Agentic deep evaluation — LLM generates cases, answers with/without skill, judges."""

from __future__ import annotations

import json

import pytest

from app.evals.deep import DeepEvaluator
from app.llm.providers.local import LocalProvider
from app.okf.concept import parse_concept

SKILL = parse_concept(
    "finance/invoice-ocr.md",
    "---\ntype: skill\ntitle: Invoice OCR\n---\n# OCR\nExtract vendor, total, line items.\n",
)


class FakeChatProvider:
    """Routes chat() by a marker in the system prompt so we can assert the flow."""

    name = "fake"
    has_chat = True
    using_real_embeddings = False

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def embed(self, texts):
        return [[0.0] for _ in texts]

    async def embed_one(self, text):
        return [0.0]

    async def chat(self, system: str, user: str) -> str:
        self.calls.append(system[:24])
        if "generate evaluation" in system:
            return json.dumps(
                [
                    {"scenario": "A normal invoice", "edge_case": False},
                    {"scenario": "A blurry, rotated invoice", "edge_case": True},
                ]
            )
        if "impartial judge" in system:
            # with-skill clearly better than without
            return json.dumps({"with_score": 9, "without_score": 4, "note": "skill helped"})
        return "an answer"


@pytest.mark.asyncio
async def test_unavailable_without_chat_provider():
    report = await DeepEvaluator(provider=LocalProvider()).evaluate(SKILL, n_cases=2)
    assert report.available is False
    assert report.reason
    assert report.cases == []


@pytest.mark.asyncio
async def test_generates_cases_and_scores_effectiveness():
    fake = FakeChatProvider()
    report = await DeepEvaluator(provider=fake).evaluate(SKILL, n_cases=2)
    assert report.available is True
    assert len(report.cases) == 2
    # one edge case flagged
    assert any(c.is_edge_case for c in report.cases)
    # with(9) - without(4) = +5 per case
    assert report.effectiveness_avg == pytest.approx(5.0)
    assert report.win_rate == pytest.approx(1.0)
    assert report.with_avg == pytest.approx(9.0)
    assert report.without_avg == pytest.approx(4.0)
    # flow: 1 generate + per case (without, with, judge)
    assert sum(1 for s in fake.calls if s.startswith("You generate")) == 1


@pytest.mark.asyncio
async def test_report_serializes():
    report = await DeepEvaluator(provider=FakeChatProvider()).evaluate(SKILL, n_cases=1)
    d = report.to_dict()
    assert set(d) >= {"available", "cases", "effectiveness_avg", "win_rate", "summary", "skipped"}


class RateLimitedProvider(FakeChatProvider):
    """Generates cases but returns None for the answer/judge calls (rate-limited)."""

    async def chat(self, system: str, user: str) -> str | None:
        if "generate evaluation" in system:
            return await super().chat(system, user)
        return None  # simulate 429 → answer/judge fail


@pytest.mark.asyncio
async def test_failed_calls_are_skipped_not_scored_zero():
    report = await DeepEvaluator(provider=RateLimitedProvider()).evaluate(SKILL, n_cases=2)
    assert report.available is True
    assert report.cases == []  # nothing scored
    assert report.skipped == 2  # both cases skipped, not scored 0
    assert report.effectiveness_avg == 0.0
