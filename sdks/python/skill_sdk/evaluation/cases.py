from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

EVAL_CASES_FILENAME = "eval_cases.yaml"
VALID_INPUT_TYPES = frozenset({"command", "event"})
VALID_EXPECT_MODES = frozenset({"exact_match", "contains", "llm_judged"})


def eval_cases_path(skill_path: str | Path) -> Path:
    return Path(skill_path) / "tests" / EVAL_CASES_FILENAME


def load_eval_cases(skill_path: str | Path) -> list[dict[str, Any]]:
    """Load declarative eval cases for a skill. Returns [] if none are authored."""
    path = eval_cases_path(skill_path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level document must be a mapping")
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError(f"{path}: 'cases' must be a list")
    errors = validate_eval_cases(cases)
    if errors:
        raise ValueError(f"{path}: invalid eval cases:\n" + "\n".join(f"  - {e}" for e in errors))
    return cases


def save_eval_cases(skill_path: str | Path, cases: list[dict[str, Any]]) -> None:
    errors = validate_eval_cases(cases)
    if errors:
        raise ValueError("invalid eval cases:\n" + "\n".join(f"  - {e}" for e in errors))
    path = eval_cases_path(skill_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"version": 1, "cases": cases}
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def validate_eval_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, case in enumerate(cases):
        prefix = f"case[{i}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue
        case_id = case.get("id")
        if not case_id or not isinstance(case_id, str):
            errors.append(f"{prefix}: missing or invalid 'id'")
        elif case_id in seen_ids:
            errors.append(f"{prefix}: duplicate id '{case_id}'")
        else:
            seen_ids.add(case_id)

        input_ = case.get("input")
        if not isinstance(input_, dict):
            errors.append(f"{prefix}: missing or invalid 'input'")
        else:
            if input_.get("type") not in VALID_INPUT_TYPES:
                errors.append(f"{prefix}.input: 'type' must be one of {sorted(VALID_INPUT_TYPES)}")
            if not input_.get("name"):
                errors.append(f"{prefix}.input: missing 'name'")

        expect = case.get("expect")
        if not isinstance(expect, dict):
            errors.append(f"{prefix}: missing or invalid 'expect'")
        else:
            mode = expect.get("mode")
            if mode not in VALID_EXPECT_MODES:
                valid = sorted(VALID_EXPECT_MODES)
                errors.append(f"{prefix}.expect: 'mode' must be one of {valid}")
            elif mode == "llm_judged" and not expect.get("rubric"):
                errors.append(f"{prefix}.expect: mode 'llm_judged' requires a 'rubric'")
            elif mode in ("exact_match", "contains") and expect.get("value") is None:
                errors.append(f"{prefix}.expect: mode '{mode}' requires a 'value'")
    return errors
