from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

EVAL_CASES_FILENAME = "eval_cases.yaml"
VALID_INPUT_TYPES = frozenset({"command", "event", "task"})
VALID_EXPECT_MODES = frozenset({"exact_match", "contains", "llm_judged", "assertions"})
VALID_ASSERTION_KINDS = frozenset(
    {"file_exists", "file_contains", "command_ran", "exit_code", "no_extra_files", "llm"}
)
VALID_BASELINE_MODES = frozenset({"auto", "with_without", "vs_previous"})

# required params per typed kind (llm handled separately)
_ASSERTION_REQUIRED = {
    "file_exists": ("path",),
    "command_ran": ("pattern",),
    "exit_code": ("equals",),
    "no_extra_files": ("allow",),
}


def validate_assertion(a: Any, prefix: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(a, dict):
        return [f"{prefix}: assertion must be a mapping"]
    kind = a.get("kind")
    if kind not in VALID_ASSERTION_KINDS:
        return [f"{prefix}: unknown assertion kind '{kind}'"]
    if kind == "llm":
        if not a.get("statement"):
            errors.append(f"{prefix}: assertion kind 'llm' requires a 'statement'")
        return errors
    if kind == "file_contains":
        if not a.get("path"):
            errors.append(f"{prefix}: 'file_contains' requires a 'path'")
        if not a.get("text") and not a.get("pattern"):
            errors.append(f"{prefix}: 'file_contains' requires 'text' or 'pattern'")
        return errors
    for req in _ASSERTION_REQUIRED.get(kind, ()):
        if a.get(req) is None:
            errors.append(f"{prefix}: '{kind}' requires '{req}'")
    return errors


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
            itype = input_.get("type")
            if itype not in VALID_INPUT_TYPES:
                errors.append(f"{prefix}.input: 'type' must be one of {sorted(VALID_INPUT_TYPES)}")
            if itype == "task":
                if not input_.get("prompt") or not isinstance(input_.get("prompt"), str):
                    errors.append(f"{prefix}.input: task requires a non-empty string 'prompt'")
                files = input_.get("files")
                if files is not None and not (
                    isinstance(files, list) and all(isinstance(f, str) for f in files)
                ):
                    errors.append(f"{prefix}.input: 'files' must be a list of strings")
            elif itype in ("command", "event") and not input_.get("name"):
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
            elif mode == "assertions":
                asserts = expect.get("assertions")
                if not isinstance(asserts, list) or not asserts:
                    errors.append(f"{prefix}.expect: mode 'assertions' requires a non-empty list")
                else:
                    for j, a in enumerate(asserts):
                        errors.extend(validate_assertion(a, f"{prefix}.expect.assertions[{j}]"))

        runs = case.get("runs")
        if runs is not None and (not isinstance(runs, int) or isinstance(runs, bool) or runs < 1):
            errors.append(f"{prefix}: 'runs' must be a positive integer")
        baseline = case.get("baseline")
        if baseline is not None and baseline not in VALID_BASELINE_MODES:
            errors.append(f"{prefix}: 'baseline' must be one of {sorted(VALID_BASELINE_MODES)}")
    return errors
