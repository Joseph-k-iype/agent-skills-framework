"""Interactive (grade-vs-expected) evaluation + versioned eval-case storage."""

from __future__ import annotations

import pytest

from app.evals.agent import GradeResult
from app.evals.grade import GradeEvaluator
from app.okf import eval_cases
from app.okf.concept import parse_concept

SKILL = parse_concept(
    "finance/invoice-ocr.md",
    "---\ntype: skill\ntitle: Invoice OCR\n---\n# OCR\nExtract vendor and total.\n",
)


class FakeAgent:
    available = True

    def __init__(self, *, score=8.0, passed=True):
        self.score = score
        self.passed = passed

    async def answer_with_skill(self, concept, scenario):
        return f"answer for: {scenario}"

    async def grade(self, *, input, expected, actual):
        return GradeResult(score=self.score, passed=self.passed, reasoning="matches")


class UnavailableAgent:
    available = False


@pytest.mark.asyncio
async def test_unavailable_agent_reports_clearly():
    cases = [{"input": "x", "expected": "y"}]
    report = await GradeEvaluator(agent=UnavailableAgent()).evaluate(SKILL, cases)
    assert report.available is False
    assert report.reason
    assert report.cases == []


@pytest.mark.asyncio
async def test_grades_cases_and_aggregates():
    cases = [
        {"input": "Extract vendor from invoice A", "expected": "Acme"},
        {"input": "Extract total from invoice A", "expected": "$10"},
    ]
    report = await GradeEvaluator(agent=FakeAgent(score=8, passed=True)).evaluate(SKILL, cases)
    assert report.available is True
    assert len(report.cases) == 2
    assert report.pass_rate == pytest.approx(1.0)
    assert report.avg_score == pytest.approx(8.0)
    assert all(c.actual.startswith("answer for:") for c in report.cases)


@pytest.mark.asyncio
async def test_blank_expected_is_flagged_not_graded():
    cases = [
        {"input": "has expected", "expected": "yes"},
        {"input": "no expected", "expected": "   "},
        {"input": "", "expected": "ignored"},  # blank input dropped entirely
    ]
    report = await GradeEvaluator(agent=FakeAgent()).evaluate(SKILL, cases)
    assert len(report.cases) == 1  # only the gradeable one
    assert report.missing_expected == 1


def test_eval_cases_roundtrip_and_path():
    assert eval_cases.cases_path("a/b/lineage.md") == "a/b/lineage.eval.yaml"
    assert eval_cases.cases_path("top.md") == "top.eval.yaml"
    cases = [{"input": "in1", "expected": "out1"}, {"input": "in2", "expected": ""}]
    text = eval_cases.dump_cases(cases)
    assert eval_cases.parse_cases(text) == cases
    assert eval_cases.parse_cases("") == []  # empty file → no cases
