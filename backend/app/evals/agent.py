"""Pydantic AI eval agent — typed structured judging with retries.

The deep evaluator and the quality LLM-judge use this instead of hand-rolled
httpx + JSON parsing. Pydantic AI gives **validated structured output** (the model
is re-prompted on a schema/range violation, via ``retries``) and we layer
exponential-backoff retries on transient upstream errors (429 / 5xx), mirroring
the OpenRouter HTTP client policy.

Scoped to the configured OpenRouter chat model (the active provider). With no key
``available`` is ``False`` and callers fall back to rules-only / "unavailable"
reports — exactly as they did before with the offline provider.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.okf.concept import Concept

log = get_logger("evals.agent")

_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4


# ── typed model outputs (replace manual JSON parsing) ──
class GenCase(BaseModel):
    scenario: str
    edge_case: bool = False


class GenCases(BaseModel):
    cases: list[GenCase] = Field(default_factory=list)


class Verdict(BaseModel):
    without_score: float = Field(ge=0, le=10)
    with_score: float = Field(ge=0, le=10)
    note: str | None = None


class Quality(BaseModel):
    score: int = Field(ge=0, le=100)
    justification: str = ""


class GradeCaseDraft(BaseModel):
    input: str
    expected: str = ""  # blank when the model can't confidently infer it


class GradeCaseDrafts(BaseModel):
    cases: list[GradeCaseDraft] = Field(default_factory=list)


class GradeResult(BaseModel):
    score: float = Field(ge=0, le=10)
    passed: bool
    reasoning: str = ""


_GEN_SYSTEM = (
    "You generate evaluation test cases for an AI skill. Given the skill, produce "
    "realistic tasks a user might ask, including tricky edge cases. Set edge_case "
    "true for the unusual / adversarial ones."
)
_PLAIN_SYSTEM = "You are a helpful assistant. Complete the user's task as well as you can."
_JUDGE_SYSTEM = (
    "You are an impartial judge. You are given a task and two candidate answers: "
    "answer A was produced WITHOUT a specialist skill, answer B WITH it. Score each "
    "0-10 for correctness and usefulness, and give one short note."
)
_QUALITY_SYSTEM = (
    "You are a senior reviewer scoring an OKF knowledge concept for correctness and "
    "completeness. Score 0-100 (higher is better) with one short sentence of justification."
)
_SUGGEST_SYSTEM = (
    "You design test cases for an AI skill. For each case give a concrete `input` (a "
    "task or prompt a user would send) and the `expected` correct output. If you cannot "
    "confidently determine the expected output, leave `expected` as an empty string — "
    "do NOT guess. Include some tricky / edge cases."
)
_GRADE_SYSTEM = (
    "You are a strict evaluator. Given a task INPUT, the EXPECTED correct output, and the "
    "ACTUAL output a skill produced, score how well ACTUAL matches EXPECTED from 0-10, "
    "decide pass (true) or fail (false), and give one short reasoning sentence. Judge "
    "correctness and completeness of meaning, not surface wording."
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


class EvalAgent:
    """Thin wrapper over a Pydantic AI model for the eval LLM calls.

    Pass ``model`` to inject a test model (``TestModel`` / ``FunctionModel``);
    otherwise the OpenRouter chat model is built lazily on first use.
    """

    def __init__(self, model: Any | None = None) -> None:
        self._model = model

    @property
    def available(self) -> bool:
        return self._model is not None or bool(settings.openrouter_api_key)

    def _build_model(self) -> Any:
        if self._model is not None:
            return self._model
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openrouter import OpenRouterProvider

        self._model = OpenAIChatModel(
            settings.chat_model,
            provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
        )
        return self._model

    async def _run(self, *, system: str, user: str, output_type: Any = str) -> Any:
        """Run the agent, retrying transient upstream failures with backoff.

        Two failure modes are retried: HTTP 429/5xx, and 200-OK responses whose
        body is broken (OpenRouter free models intermittently return
        ``finish_reason="error"``, which the strict client rejects as a parse /
        validation error). Both are transient — the same call usually succeeds on
        retry. Clearly-fatal errors (bad config, usage limits) are re-raised at once.
        """
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded, UserError

        fatal = (UserError, UsageLimitExceeded)
        # retries=2 lets Pydantic AI re-prompt the model on a schema/range violation.
        agent = Agent(self._build_model(), output_type=output_type, system_prompt=system, retries=2)
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                result = await agent.run(user)
                return result.output
            except fatal:
                raise
            except ModelHTTPError as exc:
                last_exc = exc
                if exc.status_code in _RETRY_STATUS and attempt < _MAX_ATTEMPTS - 1:
                    await self._backoff(attempt, exc.status_code)
                    continue
                raise
            except Exception as exc:  # transient upstream hiccup (e.g. bad 200 body)
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await self._backoff(attempt, "transient")
                    continue
                raise
        assert last_exc is not None  # only reached if every attempt was retryable
        raise last_exc

    async def _backoff(self, attempt: int, reason: object) -> None:
        delay = 2.0**attempt
        log.warning("eval_agent_retry", reason=str(reason), delay=delay)
        await asyncio.sleep(delay)

    # ── high-level eval calls (return None / [] on failure, never raise) ──
    async def generate_cases(self, concept: Concept, n: int) -> list[GenCase]:
        user = (
            f"Skill title: {concept.title}\nSkill type: {concept.type}\n\n"
            f"{concept.body}\n\nGenerate exactly {n} test cases."
        )
        try:
            out: GenCases = await self._run(system=_GEN_SYSTEM, user=user, output_type=GenCases)
            return [c for c in out.cases if c.scenario.strip()][:n]
        except Exception as exc:
            log.warning("eval_agent_generate_failed", error=str(exc))
            return []

    async def answer(self, system: str, scenario: str) -> str | None:
        try:
            return str(await self._run(system=system, user=scenario))
        except Exception as exc:
            log.warning("eval_agent_answer_failed", error=str(exc))
            return None

    async def answer_plain(self, scenario: str) -> str | None:
        return await self.answer(_PLAIN_SYSTEM, scenario)

    async def answer_with_skill(self, concept: Concept, scenario: str) -> str | None:
        return await self.answer(_skill_system(concept), scenario)

    async def judge(self, scenario: str, without: str, with_: str) -> Verdict | None:
        try:
            return await self._run(
                system=_JUDGE_SYSTEM,
                user=_judge_user(scenario, without, with_),
                output_type=Verdict,
            )
        except Exception as exc:
            log.warning("eval_agent_judge_failed", error=str(exc))
            return None

    async def quality_score(self, concept: Concept) -> Quality | None:
        user = f"Title: {concept.title}\nType: {concept.type}\n\n{concept.body}"
        try:
            return await self._run(system=_QUALITY_SYSTEM, user=user, output_type=Quality)
        except Exception as exc:
            log.warning("eval_agent_quality_failed", error=str(exc))
            return None

    async def suggest_cases(self, concept: Concept, n: int) -> list[GradeCaseDraft]:
        user = (
            f"Skill title: {concept.title}\nSkill type: {concept.type}\n\n"
            f"{concept.body}\n\nDesign exactly {n} test cases (input + expected output)."
        )
        try:
            out: GradeCaseDrafts = await self._run(
                system=_SUGGEST_SYSTEM, user=user, output_type=GradeCaseDrafts
            )
            return [c for c in out.cases if c.input.strip()][:n]
        except Exception as exc:
            log.warning("eval_agent_suggest_failed", error=str(exc))
            return []

    async def grade(self, *, input: str, expected: str, actual: str) -> GradeResult | None:
        user = f"INPUT:\n{input}\n\nEXPECTED:\n{expected}\n\nACTUAL:\n{actual}"
        try:
            return await self._run(system=_GRADE_SYSTEM, user=user, output_type=GradeResult)
        except Exception as exc:
            log.warning("eval_agent_grade_failed", error=str(exc))
            return None
