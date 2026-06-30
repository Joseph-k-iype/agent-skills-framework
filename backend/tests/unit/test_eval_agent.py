"""EvalAgent — real Pydantic AI models (TestModel) drive structured output + retry."""

from __future__ import annotations

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.test import TestModel

from app.evals.agent import EvalAgent, GenCase, Quality, Verdict
from app.okf.concept import parse_concept

SKILL = parse_concept(
    "finance/invoice-ocr.md",
    "---\ntype: skill\ntitle: Invoice OCR\n---\n# OCR\nExtract vendor, total.\n",
)


def test_available_reflects_injected_model(monkeypatch):
    from app.evals import agent as agent_mod

    assert EvalAgent(model=TestModel()).available is True
    # No injected model and no key → unavailable.
    monkeypatch.setattr(agent_mod.settings, "openrouter_api_key", "", raising=False)
    assert EvalAgent().available is False
    monkeypatch.setattr(agent_mod.settings, "openrouter_api_key", "sk-x", raising=False)
    assert EvalAgent().available is True


@pytest.mark.asyncio
async def test_generate_cases_returns_typed_structured_output():
    model = TestModel(
        custom_output_args={
            "cases": [
                {"scenario": "A normal invoice", "edge_case": False},
                {"scenario": "A blurry, rotated invoice", "edge_case": True},
            ]
        }
    )
    cases = await EvalAgent(model=model).generate_cases(SKILL, 5)
    assert [type(c) for c in cases] == [GenCase, GenCase]
    assert any(c.edge_case for c in cases)


@pytest.mark.asyncio
async def test_judge_and_quality_validate_ranges():
    verdict = await EvalAgent(
        model=TestModel(custom_output_args={"with_score": 9, "without_score": 4, "note": "ok"})
    ).judge("task", "a", "b")
    assert isinstance(verdict, Verdict)
    assert 0 <= verdict.without_score <= 10 and 0 <= verdict.with_score <= 10

    quality = await EvalAgent(
        model=TestModel(custom_output_args={"score": 82, "justification": "solid"})
    ).quality_score(SKILL)
    assert isinstance(quality, Quality)
    assert 0 <= quality.score <= 100


class _Flaky(TestModel):
    """Raises a 429 for the first ``fail_times`` requests, then behaves normally."""

    def __init__(self, fail_times: int, **kw):
        super().__init__(**kw)
        self._remaining = fail_times
        self.attempts = 0

    def request(self, messages, model_settings, model_request_parameters):
        self.attempts += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise ModelHTTPError(status_code=429, model_name="test", body=None)
        return super().request(messages, model_settings, model_request_parameters)


@pytest.mark.asyncio
async def test_retries_transient_429_then_succeeds(monkeypatch):
    # Skip the backoff sleeps so the test is fast.
    async def _no_sleep(_):
        return None

    monkeypatch.setattr("app.evals.agent.asyncio.sleep", _no_sleep)
    model = _Flaky(fail_times=2, custom_output_args={"score": 70, "justification": "ok"})
    quality = await EvalAgent(model=model).quality_score(SKILL)
    assert isinstance(quality, Quality)
    assert model.attempts == 3  # two 429s, third succeeded


class _FlakyParse(TestModel):
    """Raises a non-HTTP error (like a bad 200 body) the first ``fail_times`` times."""

    def __init__(self, fail_times: int, **kw):
        super().__init__(**kw)
        self._remaining = fail_times
        self.attempts = 0

    def request(self, messages, model_settings, model_request_parameters):
        self.attempts += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise ValueError("Invalid response: finish_reason='error'")
        return super().request(messages, model_settings, model_request_parameters)


@pytest.mark.asyncio
async def test_retries_transient_bad_response_then_succeeds(monkeypatch):
    async def _no_sleep(_):
        return None

    monkeypatch.setattr("app.evals.agent.asyncio.sleep", _no_sleep)
    model = _FlakyParse(
        fail_times=2,
        custom_output_args={
            "cases": [{"scenario": "x", "edge_case": False}],
        },
    )
    cases = await EvalAgent(model=model).generate_cases(SKILL, 3)
    assert [c.scenario for c in cases] == ["x"]
    assert model.attempts == 3  # two bad bodies, third succeeded


@pytest.mark.asyncio
async def test_persistent_429_gives_up_gracefully(monkeypatch):
    async def _no_sleep(_):
        return None

    monkeypatch.setattr("app.evals.agent.asyncio.sleep", _no_sleep)
    model = _Flaky(fail_times=99, custom_output_args={"score": 70, "justification": "ok"})
    # Never raises to the caller — returns None after exhausting attempts.
    assert await EvalAgent(model=model).quality_score(SKILL) is None
    assert model.attempts == 4  # _MAX_ATTEMPTS
