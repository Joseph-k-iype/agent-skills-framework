import tempfile
from pathlib import Path

import pytest

from skill_sdk.evaluation.cases import (
    eval_cases_path,
    load_eval_cases,
    save_eval_cases,
    validate_eval_cases,
)

EXACT_CASE = {
    "id": "case-1",
    "description": "basic",
    "input": {"type": "command", "name": "discover", "args": ["--source", "x.csv"]},
    "expect": {"mode": "exact_match", "value": {"status": "success"}},
}

LLM_CASE = {
    "id": "case-2",
    "description": "rubric scored",
    "input": {"type": "event", "name": "tag"},
    "expect": {"mode": "llm_judged", "rubric": "Score 0-100"},
}


def test_load_returns_empty_when_file_missing():
    tmp = Path(tempfile.mkdtemp())
    assert load_eval_cases(tmp) == []


def test_save_then_load_round_trip():
    tmp = Path(tempfile.mkdtemp())
    save_eval_cases(tmp, [EXACT_CASE, LLM_CASE])
    loaded = load_eval_cases(tmp)
    assert [c["id"] for c in loaded] == ["case-1", "case-2"]
    assert eval_cases_path(tmp).exists()


def test_validate_accepts_well_formed_cases():
    assert validate_eval_cases([EXACT_CASE, LLM_CASE]) == []


def test_validate_rejects_duplicate_ids():
    errors = validate_eval_cases([EXACT_CASE, dict(EXACT_CASE)])
    assert any("duplicate id" in e for e in errors)


def test_validate_rejects_missing_input():
    bad = {"id": "x", "expect": {"mode": "exact_match", "value": 1}}
    errors = validate_eval_cases([bad])
    assert any("input" in e for e in errors)


def test_validate_rejects_llm_judged_without_rubric():
    bad = {
        "id": "x",
        "input": {"type": "command", "name": "y"},
        "expect": {"mode": "llm_judged"},
    }
    errors = validate_eval_cases([bad])
    assert any("rubric" in e for e in errors)


def test_validate_rejects_exact_match_without_value():
    bad = {
        "id": "x",
        "input": {"type": "command", "name": "y"},
        "expect": {"mode": "exact_match"},
    }
    errors = validate_eval_cases([bad])
    assert any("value" in e for e in errors)


def test_save_rejects_invalid_cases():
    tmp = Path(tempfile.mkdtemp())
    with pytest.raises(ValueError):
        save_eval_cases(tmp, [{"id": "bad"}])


def test_load_raises_on_malformed_existing_file():
    tmp = Path(tempfile.mkdtemp())
    path = eval_cases_path(tmp)
    path.parent.mkdir(parents=True)
    path.write_text("version: 1\ncases:\n  - id: x\n")
    with pytest.raises(ValueError):
        load_eval_cases(tmp)


def _task_case(**over):
    case = {
        "id": "t1",
        "input": {"type": "task", "prompt": "do the thing"},
        "expect": {
            "mode": "assertions",
            "assertions": [{"kind": "file_exists", "path": "out.txt"}],
        },
    }
    case.update(over)
    return case


def test_valid_task_case_has_no_errors():
    assert validate_eval_cases([_task_case()]) == []


def test_task_case_requires_prompt():
    case = _task_case(input={"type": "task"})
    errs = validate_eval_cases([case])
    assert any("prompt" in e for e in errs)


def test_assertions_mode_requires_nonempty_list():
    case = _task_case(expect={"mode": "assertions", "assertions": []})
    errs = validate_eval_cases([case])
    assert any("assertions" in e for e in errs)


def test_unknown_assertion_kind_is_error():
    case = _task_case(expect={"mode": "assertions", "assertions": [{"kind": "bogus"}]})
    errs = validate_eval_cases([case])
    assert any("bogus" in e for e in errs)


def test_file_contains_requires_text_or_pattern():
    case = _task_case(expect={"mode": "assertions",
                              "assertions": [{"kind": "file_contains", "path": "a.txt"}]})
    errs = validate_eval_cases([case])
    assert any("file_contains" in e for e in errs)


def test_command_assertion_without_execute_permission_is_warning_not_error():
    # validate_eval_cases is permission-agnostic; the execute warning is added
    # by validate_full_skill integration (Task 8). Here we only confirm the
    # case itself is structurally valid.
    case = _task_case(expect={"mode": "assertions",
                              "assertions": [{"kind": "command_ran", "pattern": "npm install"}]})
    assert validate_eval_cases([case]) == []


def test_runs_must_be_positive_int_and_baseline_enum():
    bad_runs = _task_case(runs=0)
    bad_baseline = _task_case(baseline="sometimes")
    assert any("runs" in e for e in validate_eval_cases([bad_runs]))
    assert any("baseline" in e for e in validate_eval_cases([bad_baseline]))


def test_task_type_does_not_require_input_name():
    # 'name' is required for command/event but not for task
    assert validate_eval_cases([_task_case()]) == []
