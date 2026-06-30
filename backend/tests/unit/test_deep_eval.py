"""Agentic deep evaluation — aggregation over a (faked) eval agent.

The LLM plumbing lives in :class:`app.evals.agent.EvalAgent` (tested separately
with real Pydantic AI models in ``test_eval_agent.py``). Here we inject a fake
agent so we can assert DeepEvaluator's flow and scoring deterministically.
"""

from __future__ import annotations

import pytest

from app.evals.agent import GenCase, Verdict
from app.evals.deep import DeepEvaluator
from app.okf.concept import parse_concept

SKILL = parse_concept(
    "finance/invoice-ocr.md",
    "---\ntype: skill\ntitle: Invoice OCR\n---\n# OCR\nExtract vendor, total, line items.\n",
)


class FakeAgent:
    """Implements the EvalAgent high-level interface deterministically."""

    available = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_cases(self, concept, n):
        self.calls.append("generate")
        cases = [
            GenCase(scenario="A normal invoice", edge_case=False),
            GenCase(scenario="A blurry, rotated invoice", edge_case=True),
        ]
        return cases[:n]

    async def answer_plain(self, scenario):
        self.calls.append("plain")
        return "a plain answer"

    async def answer_with_skill(self, concept, scenario):
        self.calls.append("skill")
        return "a skilled answer"

    async def judge(self, scenario, without, with_):
        self.calls.append("judge")
        return Verdict(with_score=9, without_score=4, note="skill helped")


class UnavailableAgent:
    available = False


class RateLimitedAgent(FakeAgent):
    """Generates cases but every answer is rate-limited (None)."""

    async def answer_plain(self, scenario):
        return None

    async def answer_with_skill(self, concept, scenario):
        return None


@pytest.mark.asyncio
async def test_unavailable_without_chat_provider():
    report = await DeepEvaluator(agent=UnavailableAgent()).evaluate(SKILL, n_cases=2)
    assert report.available is False
    assert report.reason
    assert report.cases == []


@pytest.mark.asyncio
async def test_generates_cases_and_scores_effectiveness():
    fake = FakeAgent()
    report = await DeepEvaluator(agent=fake).evaluate(SKILL, n_cases=2)
    assert report.available is True
    assert len(report.cases) == 2
    assert any(c.is_edge_case for c in report.cases)
    # with(9) - without(4) = +5 per case
    assert report.effectiveness_avg == pytest.approx(5.0)
    assert report.win_rate == pytest.approx(1.0)
    assert report.with_avg == pytest.approx(9.0)
    assert report.without_avg == pytest.approx(4.0)
    assert fake.calls.count("generate") == 1


@pytest.mark.asyncio
async def test_report_serializes():
    report = await DeepEvaluator(agent=FakeAgent()).evaluate(SKILL, n_cases=1)
    d = report.to_dict()
    assert set(d) >= {"available", "cases", "effectiveness_avg", "win_rate", "summary", "skipped"}


@pytest.mark.asyncio
async def test_failed_calls_are_skipped_not_scored_zero():
    report = await DeepEvaluator(agent=RateLimitedAgent()).evaluate(SKILL, n_cases=2)
    assert report.available is True
    assert report.cases == []  # nothing scored
    assert report.skipped == 2  # both cases skipped, not scored 0
    assert report.effectiveness_avg == 0.0
