"""Evaluator base: rules always run, LLM judge only when a provider has chat."""

from __future__ import annotations

import pytest

from app.evals.base import EvalFinding, EvalResult, Evaluator
from app.llm.providers.local import LocalProvider
from app.okf.concept import parse_concept


class _DummyRulesEvaluator(Evaluator):
    name = "dummy"

    def run_rules(self, concept, bundle_files):
        return EvalResult(
            evaluator=self.name,
            score=80.0,
            findings=[EvalFinding(severity="info", message="ok")],
            blocking=False,
            used_llm=False,
        )


@pytest.mark.asyncio
async def test_rules_only_under_local_provider():
    c = parse_concept("a.md", "---\ntype: skill\n---\nbody")
    result = await _DummyRulesEvaluator().evaluate(c, LocalProvider(), [])
    assert result.evaluator == "dummy"
    assert result.used_llm is False
    assert result.score == 80.0
    assert result.findings[0].message == "ok"


@pytest.mark.asyncio
async def test_llm_judge_skipped_when_no_chat():
    class WithJudge(_DummyRulesEvaluator):
        async def run_llm_judge(self, concept, provider):
            raise AssertionError("should not be called when provider has no chat")

    c = parse_concept("a.md", "---\ntype: skill\n---\nbody")
    result = await WithJudge().evaluate(c, LocalProvider(), [])
    assert result.used_llm is False
