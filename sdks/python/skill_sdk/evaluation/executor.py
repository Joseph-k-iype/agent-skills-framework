from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

_REPO_ROOT_DEPTH = 4  # executor.py -> evaluation -> skill_sdk -> python -> sdks -> <repo root>


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[_REPO_ROOT_DEPTH]


def _get_harness_cls():
    """Lazily import the testing harness, falling back to a sys.path shim.

    ``testing/harness.py`` only imports *from* ``skill_sdk`` (never the
    reverse), and is outside the ``sdks/python`` root that's on ``PYTHONPATH``
    in contexts like the frontend backend — mirrors the existing shim at
    ``cli/src/main.py:9``.
    """
    try:
        from testing.harness import SkillTestHarness
    except ImportError:
        import sys

        repo_root = str(_repo_root())
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from testing.harness import SkillTestHarness
    return SkillTestHarness


def _flatten_result(status: str, data: dict[str, Any], error: str | None, message: str) -> dict[str, Any]:
    flat: dict[str, Any] = {"status": status, "error": error, "message": message}
    flat.update(data or {})
    return flat


def _exact_match(actual: dict[str, Any], expected: Any) -> bool:
    """Every key in ``expected`` must be present in ``actual`` with an equal value.

    A deliberate *subset* check, not full dict equality — a case author
    usually only cares about a few fields (e.g. ``status``), not every key a
    skill happens to return.
    """
    if not isinstance(expected, dict):
        return actual.get("status") == expected
    return all(k in actual and actual[k] == v for k, v in expected.items())


def _contains(actual: dict[str, Any], expected: Any) -> bool:
    """Looser than exact_match: strings use substring containment, collections
    use membership, everything else falls back to equality."""
    if not isinstance(expected, dict):
        return str(expected) in json.dumps(actual, default=str)
    for k, v in expected.items():
        if k not in actual:
            return False
        av = actual[k]
        if isinstance(av, str) and isinstance(v, str):
            if v not in av:
                return False
        elif isinstance(av, list | dict):
            if v not in av:
                return False
        elif av != v:
            return False
    return True


def execute_case(skill_path: str | Path, case: dict[str, Any]) -> dict[str, Any]:
    """Run one declarative eval case against the real skill via the test harness.

    exact_match/contains cases are scored here deterministically — zero LLM
    calls, zero optional dependencies — so this always runs, even when the
    ``eval`` extras aren't installed. llm_judged cases come back with
    ``status="pending_judgment"`` plus the raw output/rubric for an agent to
    score.
    """
    case_id = case.get("id", "?")
    expect = case.get("expect", {})
    mode = expect.get("mode")
    input_ = case.get("input", {})

    try:
        harness_cls = _get_harness_cls()
        harness = harness_cls(skill_path)

        async def _run():
            await harness.initialize()
            if input_.get("type") == "command":
                return await harness.run_command(input_.get("name"), input_.get("args"))
            return await harness.run_event(input_.get("name"), input_.get("payload"))

        result = asyncio.run(_run())
        actual = _flatten_result(result.status, result.data, result.error, result.message)
    except Exception as e:
        return {
            "case_id": case_id,
            "mode": mode,
            "status": "error",
            "detail": f"{type(e).__name__}: {e}",
        }

    if mode == "exact_match":
        passed = _exact_match(actual, expect.get("value"))
        return {"case_id": case_id, "mode": mode, "status": "passed" if passed else "failed", "actual": actual}
    if mode == "contains":
        passed = _contains(actual, expect.get("value"))
        return {"case_id": case_id, "mode": mode, "status": "passed" if passed else "failed", "actual": actual}
    if mode == "llm_judged":
        return {
            "case_id": case_id,
            "mode": mode,
            "status": "pending_judgment",
            "actual": actual,
            "rubric": expect.get("rubric"),
        }
    return {"case_id": case_id, "mode": mode, "status": "error", "detail": f"unknown expect.mode '{mode}'"}
