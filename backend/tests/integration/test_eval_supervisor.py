"""Eval supervisor aggregation — works offline (rules-only) under local provider."""

from __future__ import annotations

import pytest

from app.evals.supervisor import EvalSupervisor
from app.okf.concept import parse_concept

pytestmark = pytest.mark.asyncio

CLEAN = parse_concept(
    "finance/invoice-ocr.md",
    "---\ntype: skill\ntitle: Invoice OCR\ndescription: Extracts line items\n"
    "tags: [finance]\n---\n# Overview\n\nUses OCR.\n\n```python\nx = 1\n```\n",
)

SECRET = parse_concept(
    "a.md",
    "---\ntype: skill\ntitle: Bad\ndescription: x\ntags: [x]\n---\n"
    "# Body\nAWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n",
)


async def test_clean_concept_passes():
    report = await EvalSupervisor().evaluate(CLEAN, ["finance/invoice-ocr.md"])
    assert len(report.results) == 6
    assert report.passed is True
    assert not report.blocking_issues
    assert report.overall_score > 70.0


async def test_secret_concept_is_blocked():
    clean = await EvalSupervisor().evaluate(CLEAN, ["finance/invoice-ocr.md"])
    report = await EvalSupervisor().evaluate(SECRET, ["a.md"])
    assert report.passed is False
    assert any("security" in b.lower() for b in report.blocking_issues)
    assert report.overall_score < clean.overall_score


async def test_report_serializes_to_dict():
    report = await EvalSupervisor().evaluate(CLEAN, ["finance/invoice-ocr.md"])
    d = report.to_dict()
    assert set(d) >= {"overall_score", "confidence", "passed", "results", "blocking_issues"}
    assert isinstance(d["results"], list) and len(d["results"]) == 6
