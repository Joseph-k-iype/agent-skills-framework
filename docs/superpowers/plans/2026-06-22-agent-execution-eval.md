# Agent-Execution Baseline Evaluation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an agent-execution eval mode to `skill_sdk.evaluation` that runs a real LLM agent over a skill's `SKILL.md` in a permission-scoped sandbox and grades the workspace + trajectory against a baseline (with/without skill, or vs previous version).

**Architecture:** Additive extension of the existing evaluation module. New single-purpose modules (`trajectory`, `assertions`, `sandbox`, `agent_exec`, `baseline`) feed a new `agent_execution` section on `EvaluationReport`. `evaluate_skill` calls the new pass after the existing deterministic + agentic passes, only when `task` cases exist and a model is available; otherwise it degrades to a skipped section (existing graceful-degradation contract preserved).

**Tech Stack:** Python 3.11+, LangChain 1.0 / langchain-core 1.0 (eval extra), pyyaml, pytest + pytest-asyncio. Tests drive model-dependent code with the existing `FakeToolCallingChatModel` double — no network calls.

**Reference spec:** `docs/superpowers/specs/2026-06-22-agent-execution-baseline-eval-design.md`

## Global Constraints

- Python 3.11+; ruff line-length 100, rules E/F/I/UP (`sdks/python/pyproject.toml`).
- Model-dependent code lives behind the `eval` extra (`langchain-core>=1.0`, `langchain>=1.0`, `langgraph>=1.0`, `python-dotenv>=1.0`). Importing it without the extra must degrade, never crash `validate`/`build`/`publish`/CI.
- Never raise for a missing/misconfigured judge — mirror `graph._build_model` (returns `None` on any failure).
- Permission action vocabulary is fixed: `{read, write, create, delete, list, execute}` (`validation.py:240`).
- All new SDK modules run from `cd sdks/python && python -m pytest`. Tests import the model double via `from _fake_chat_model import FakeToolCallingChatModel` (lives at `sdks/python/tests/_fake_chat_model.py`).
- `EvaluationReport.to_dict()` is the API/CLI serialization boundary — every new field must be represented there.
- Sandbox is pragmatic, NOT true isolation (cwd lock + minimized env + timeout + destructive-pattern deny-list). Document the limitation; do not claim real isolation.

---

### Task 1: Case schema — `task` input type + `assertions` expect mode

**Files:**
- Modify: `sdks/python/skill_sdk/evaluation/cases.py`
- Test: `sdks/python/tests/test_evaluation_cases.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `VALID_INPUT_TYPES` now includes `"task"`; `VALID_EXPECT_MODES` includes `"assertions"`. `validate_eval_cases(cases: list[dict]) -> list[str]` (signature unchanged) now validates task cases. New module constant `VALID_ASSERTION_KINDS = frozenset({"file_exists", "file_contains", "command_ran", "exit_code", "no_extra_files", "llm"})` and helper `validate_assertion(a: dict, prefix: str) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

```python
# append to sdks/python/tests/test_evaluation_cases.py
from skill_sdk.evaluation.cases import validate_eval_cases


def _task_case(**over):
    case = {
        "id": "t1",
        "input": {"type": "task", "prompt": "do the thing"},
        "expect": {"mode": "assertions", "assertions": [{"kind": "file_exists", "path": "out.txt"}]},
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_cases.py -q`
Expected: FAIL — task cases currently rejected (`'type' must be one of ['command', 'event']`).

- [ ] **Step 3: Implement the schema changes**

```python
# sdks/python/skill_sdk/evaluation/cases.py — replace the constants and add helpers
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
```

Then update `validate_eval_cases` — replace the `input` and `expect` blocks:

```python
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
                errors.append(f"{prefix}.expect: 'mode' must be one of {sorted(VALID_EXPECT_MODES)}")
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_cases.py -q`
Expected: PASS (all, including pre-existing command/event tests).

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/cases.py sdks/python/tests/test_evaluation_cases.py
git commit -m "feat(eval): add task input type and assertions expect mode to case schema

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Trajectory & RunResult dataclasses

**Files:**
- Create: `sdks/python/skill_sdk/evaluation/trajectory.py`
- Test: `sdks/python/tests/test_evaluation_trajectory.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `TrajectoryEvent(kind: str, name: str, args: dict = {}, output: str = "", exit_code: int | None = None)`
  - `Trajectory(events: list[TrajectoryEvent] = [], tokens_in: int = 0, tokens_out: int = 0, duration_ms: int = 0)` with `add(event)`, `commands() -> list[TrajectoryEvent]` (events where `kind == "command"`), and `to_dict() -> dict`.
  - `RunResult(final_text: str = "", workspace_path: str = "", trajectory: Trajectory = Trajectory(), permission_violations: list[str] = [], error: str | None = None)` with `to_dict()`.
  - This module is pure (no model, no langchain import).

- [ ] **Step 1: Write the failing test**

```python
# sdks/python/tests/test_evaluation_trajectory.py
from skill_sdk.evaluation.trajectory import RunResult, Trajectory, TrajectoryEvent


def test_commands_filters_command_events():
    t = Trajectory()
    t.add(TrajectoryEvent(kind="tool", name="read_file"))
    t.add(TrajectoryEvent(kind="command", name="npm install", exit_code=0))
    cmds = t.commands()
    assert len(cmds) == 1
    assert cmds[0].name == "npm install"


def test_trajectory_to_dict_roundtrips_counts():
    t = Trajectory(tokens_in=10, tokens_out=5, duration_ms=1200)
    t.add(TrajectoryEvent(kind="command", name="ls", output="a\nb", exit_code=0))
    d = t.to_dict()
    assert d["tokens_in"] == 10
    assert d["tokens_out"] == 5
    assert d["duration_ms"] == 1200
    assert d["events"][0]["name"] == "ls"


def test_runresult_to_dict_includes_trajectory_and_violations():
    r = RunResult(final_text="done", workspace_path="/tmp/x",
                  permission_violations=["execute not declared"])
    d = r.to_dict()
    assert d["final_text"] == "done"
    assert d["permission_violations"] == ["execute not declared"]
    assert "trajectory" in d
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_trajectory.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `trajectory.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryEvent:
    kind: str  # "tool" | "command"
    name: str  # tool name, or the command string for commands
    args: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "args": self.args,
            "output": self.output,
            "exit_code": self.exit_code,
        }


@dataclass
class Trajectory:
    events: list[TrajectoryEvent] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0

    def add(self, event: TrajectoryEvent) -> None:
        self.events.append(event)

    def commands(self) -> list[TrajectoryEvent]:
        return [e for e in self.events if e.kind == "command"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "duration_ms": self.duration_ms,
        }


@dataclass
class RunResult:
    final_text: str = ""
    workspace_path: str = ""
    trajectory: Trajectory = field(default_factory=Trajectory)
    permission_violations: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_text": self.final_text,
            "workspace_path": self.workspace_path,
            "trajectory": self.trajectory.to_dict(),
            "permission_violations": self.permission_violations,
            "error": self.error,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_trajectory.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/trajectory.py sdks/python/tests/test_evaluation_trajectory.py
git commit -m "feat(eval): add Trajectory and RunResult dataclasses

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Typed deterministic assertions

**Files:**
- Create: `sdks/python/skill_sdk/evaluation/assertions.py`
- Test: `sdks/python/tests/test_evaluation_assertions.py`

**Interfaces:**
- Consumes: `RunResult`, `Trajectory` from `trajectory.py`.
- Produces: `evaluate_assertions(case: dict, result: RunResult, input_files: list[str] | None = None) -> list[dict]`. Returns one dict per **typed** assertion (skips `kind == "llm"`, which the judge handles in Task 6): `{"kind": str, "spec": dict, "passed": bool, "evidence": str}`. Pure — reads files from `result.workspace_path` and events from `result.trajectory`.

- [ ] **Step 1: Write the failing tests**

```python
# sdks/python/tests/test_evaluation_assertions.py
import tempfile
from pathlib import Path

from skill_sdk.evaluation.assertions import evaluate_assertions
from skill_sdk.evaluation.trajectory import RunResult, Trajectory, TrajectoryEvent


def _ws_with(files: dict[str, str]) -> str:
    ws = Path(tempfile.mkdtemp())
    for rel, content in files.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return str(ws)


def test_file_exists_glob_pass_and_fail():
    ws = _ws_with({"src/App.tsx": "x", "package.json": "{}"})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "file_exists", "path": "src/*.tsx"},
        {"kind": "file_exists", "path": "missing.txt"},
    ]}}
    out = evaluate_assertions(case, res)
    assert out[0]["passed"] is True
    assert out[1]["passed"] is False


def test_file_contains_text():
    ws = _ws_with({"src/index.css": '@import "tailwindcss";'})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "file_contains", "path": "src/index.css", "text": '@import "tailwindcss"'},
    ]}}
    assert evaluate_assertions(case, res)[0]["passed"] is True


def test_command_ran_substring_and_regex():
    traj = Trajectory()
    traj.add(TrajectoryEvent(kind="command", name="npm install --silent", exit_code=0))
    res = RunResult(trajectory=traj)
    case = {"expect": {"assertions": [
        {"kind": "command_ran", "pattern": "npm install"},
        {"kind": "command_ran", "pattern": "/npm (install|ci)/"},
        {"kind": "command_ran", "pattern": "yarn add"},
    ]}}
    out = evaluate_assertions(case, res)
    assert [o["passed"] for o in out] == [True, True, False]


def test_exit_code_matches_named_command():
    traj = Trajectory()
    traj.add(TrajectoryEvent(kind="command", name="npm run build", exit_code=0))
    res = RunResult(trajectory=traj)
    case = {"expect": {"assertions": [{"kind": "exit_code", "command": "npm run build", "equals": 0}]}}
    assert evaluate_assertions(case, res)[0]["passed"] is True


def test_no_extra_files_respects_allowlist_and_inputs():
    ws = _ws_with({"package.json": "{}", "node_modules/x.js": "x", "stray.tmp": "junk",
                   "data.csv": "given"})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "no_extra_files", "allow": ["package.json", "node_modules/**"]},
    ]}}
    out = evaluate_assertions(case, res, input_files=["data.csv"])
    assert out[0]["passed"] is False
    assert "stray.tmp" in out[0]["evidence"]


def test_llm_assertions_are_skipped_here():
    res = RunResult()
    case = {"expect": {"assertions": [{"kind": "llm", "statement": "looks good"}]}}
    assert evaluate_assertions(case, res) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_assertions.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `assertions.py`**

```python
from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from .trajectory import RunResult


def _match_pattern(text: str, pattern: str) -> bool:
    """A /slash-wrapped/ pattern is a regex; anything else is a substring."""
    if len(pattern) >= 2 and pattern.startswith("/") and pattern.endswith("/"):
        return re.search(pattern[1:-1], text) is not None
    return pattern in text


def _workspace_files(ws: Path) -> list[str]:
    return [str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()]


def _file_exists(ws: Path, spec: dict) -> tuple[bool, str]:
    pattern = spec.get("path", "")
    matches = fnmatch.filter(_workspace_files(ws), pattern)
    if matches:
        return True, f"matched {matches[:5]}"
    return False, f"no file matched '{pattern}'"


def _file_contains(ws: Path, spec: dict) -> tuple[bool, str]:
    pattern = spec.get("path", "")
    text = spec.get("text")
    rx = spec.get("pattern")
    for rel in fnmatch.filter(_workspace_files(ws), pattern):
        content = (ws / rel).read_text(encoding="utf-8", errors="replace")
        if text is not None and text in content:
            return True, f"'{text}' found in {rel}"
        if rx is not None and re.search(rx, content):
            return True, f"/{rx}/ matched in {rel}"
    needle = text if text is not None else f"/{rx}/"
    return False, f"{needle!r} not found in any '{pattern}'"


def _command_ran(res: RunResult, spec: dict) -> tuple[bool, str]:
    pattern = spec.get("pattern", "")
    for ev in res.trajectory.commands():
        if _match_pattern(ev.name, pattern):
            return True, f"command '{ev.name}' matched"
    return False, f"no command matched '{pattern}'"


def _exit_code(res: RunResult, spec: dict) -> tuple[bool, str]:
    equals = spec.get("equals")
    cmd_pat = spec.get("command")
    cmds = res.trajectory.commands()
    if cmd_pat:
        cmds = [c for c in cmds if _match_pattern(c.name, cmd_pat)]
    if not cmds:
        return False, f"no command matched '{cmd_pat}'"
    last = cmds[-1]
    ok = last.exit_code == equals
    return ok, f"'{last.name}' exited {last.exit_code} (wanted {equals})"


def _no_extra_files(ws: Path, spec: dict, input_files: list[str]) -> tuple[bool, str]:
    allow = list(spec.get("allow", [])) + [Path(f).name for f in input_files] + list(input_files)
    extras = []
    for rel in _workspace_files(ws):
        if any(fnmatch.fnmatch(rel, pat) for pat in allow):
            continue
        extras.append(rel)
    if extras:
        return False, f"unexpected files: {sorted(extras)[:10]}"
    return True, "no files beyond inputs + allowlist"


def evaluate_assertions(
    case: dict[str, Any], result: RunResult, input_files: list[str] | None = None
) -> list[dict[str, Any]]:
    input_files = input_files or []
    ws = Path(result.workspace_path) if result.workspace_path else None
    out: list[dict[str, Any]] = []
    for spec in case.get("expect", {}).get("assertions", []):
        kind = spec.get("kind")
        if kind == "llm":
            continue
        try:
            if kind == "file_exists":
                passed, evidence = _file_exists(ws, spec)
            elif kind == "file_contains":
                passed, evidence = _file_contains(ws, spec)
            elif kind == "command_ran":
                passed, evidence = _command_ran(result, spec)
            elif kind == "exit_code":
                passed, evidence = _exit_code(result, spec)
            elif kind == "no_extra_files":
                passed, evidence = _no_extra_files(ws, spec, input_files)
            else:
                passed, evidence = False, f"unknown kind '{kind}'"
        except Exception as e:  # a malformed workspace must not crash the suite
            passed, evidence = False, f"{type(e).__name__}: {e}"
        out.append({"kind": kind, "spec": spec, "passed": passed, "evidence": evidence})
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_assertions.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/assertions.py sdks/python/tests/test_evaluation_assertions.py
git commit -m "feat(eval): add typed deterministic assertions over RunResult

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Sandbox — workspace + permission-scoped tools + shell deny-list

**Files:**
- Create: `sdks/python/skill_sdk/evaluation/sandbox.py`
- Test: `sdks/python/tests/test_evaluation_sandbox.py`

**Interfaces:**
- Consumes: `Trajectory`, `TrajectoryEvent` from `trajectory.py`. Imports `langchain_core.tools.StructuredTool` lazily inside `build_tools` (eval extra).
- Produces:
  - `actions_for(permissions: list[dict]) -> set[str]` — union of declared actions.
  - `Workspace(path: Path, actions: set[str], violations: list[str], input_files: list[str])`.
  - `make_workspace(permissions: list[dict], files: list[str] | None = None, skill_path: Path | None = None, base_dir: Path | None = None) -> Workspace` — creates a temp dir, copies `files` (resolved relative to `skill_path`) into it.
  - `cleanup(ws: Workspace, keep: bool = False) -> None`.
  - `build_tools(ws: Workspace, trajectory: Trajectory, full_surface: bool = False) -> list` — returns LangChain tools whose availability is gated by `ws.actions` (or all of fs+execute when `full_surface=True`, for the baseline config). Each tool records a `TrajectoryEvent`; a denied-capability call appends to `ws.violations` and returns an error string.
  - `run_command(cmd: str, cwd: Path, timeout_s: int = 60) -> tuple[int, str]` — pragmatic shell exec; raises `DestructiveCommandError` for deny-listed patterns.
  - `DESTRUCTIVE_PATTERNS: list[str]`, `DestructiveCommandError(Exception)`.

- [ ] **Step 1: Write the failing tests**

```python
# sdks/python/tests/test_evaluation_sandbox.py
import tempfile
from pathlib import Path

import pytest

from skill_sdk.evaluation.sandbox import (
    DestructiveCommandError,
    actions_for,
    build_tools,
    make_workspace,
    run_command,
)
from skill_sdk.evaluation.trajectory import Trajectory

PERMS_FS = [{"resource": "workspace", "actions": ["read", "write", "create", "list"]}]
PERMS_NONE = []


def test_actions_for_unions():
    perms = [{"resource": "a", "actions": ["read"]}, {"resource": "b", "actions": ["write", "read"]}]
    assert actions_for(perms) == {"read", "write"}


def test_make_workspace_copies_input_files():
    skill = Path(tempfile.mkdtemp())
    (skill / "tests").mkdir()
    (skill / "tests" / "data.csv").write_text("a,b")
    ws = make_workspace(PERMS_FS, files=["tests/data.csv"], skill_path=skill)
    assert (ws.path / "data.csv").read_text() == "a,b"


def test_write_tool_present_when_declared_records_event():
    ws = make_workspace(PERMS_FS)
    traj = Trajectory()
    tools = {t.name: t for t in build_tools(ws, traj)}
    assert "write_file" in tools
    tools["write_file"].invoke({"path": "out.txt", "content": "hi"})
    assert (ws.path / "out.txt").read_text() == "hi"
    assert any(e.name == "write_file" for e in traj.events)


def test_execute_tool_absent_when_not_declared():
    ws = make_workspace(PERMS_FS)  # no "execute"
    tools = {t.name: t for t in build_tools(ws, Trajectory())}
    assert "run_command" not in tools


def test_full_surface_grants_everything_for_baseline():
    ws = make_workspace(PERMS_NONE)
    tools = {t.name: t for t in build_tools(ws, Trajectory(), full_surface=True)}
    assert "run_command" in tools
    assert "write_file" in tools


def test_run_command_blocks_destructive():
    ws = make_workspace(PERMS_FS)
    with pytest.raises(DestructiveCommandError):
        run_command("rm -rf /", ws.path)


def test_run_command_runs_in_workspace():
    ws = make_workspace(PERMS_FS)
    code, out = run_command("echo hello > note.txt", ws.path)
    assert code == 0
    assert (ws.path / "note.txt").read_text().strip() == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_sandbox.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `sandbox.py`**

```python
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .trajectory import Trajectory, TrajectoryEvent

DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r":\(\)\s*\{\s*:\|:&\s*\};:",      # fork bomb
    r"\bcurl\b[^|]*\|\s*(sh|bash)\b",  # curl | sh
    r"\bwget\b[^|]*\|\s*(sh|bash)\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
]


class DestructiveCommandError(Exception):
    pass


@dataclass
class Workspace:
    path: Path
    actions: set[str]
    violations: list[str] = field(default_factory=list)
    input_files: list[str] = field(default_factory=list)


def actions_for(permissions: list[dict]) -> set[str]:
    out: set[str] = set()
    for p in permissions or []:
        for a in p.get("actions", []):
            out.add(a)
    return out


def make_workspace(
    permissions: list[dict],
    files: list[str] | None = None,
    skill_path: Path | None = None,
    base_dir: Path | None = None,
) -> Workspace:
    path = Path(tempfile.mkdtemp(prefix="skill-eval-", dir=str(base_dir) if base_dir else None))
    copied: list[str] = []
    for rel in files or []:
        src = (skill_path / rel) if skill_path else Path(rel)
        if src.exists():
            dest = path / Path(rel).name
            shutil.copy2(src, dest)
            copied.append(dest.name)
    return Workspace(path=path, actions=actions_for(permissions), input_files=copied)


def cleanup(ws: Workspace, keep: bool = False) -> None:
    if not keep:
        shutil.rmtree(ws.path, ignore_errors=True)


def run_command(cmd: str, cwd: Path, timeout_s: int = 60) -> tuple[int, str]:
    for pat in DESTRUCTIVE_PATTERNS:
        if re.search(pat, cmd):
            raise DestructiveCommandError(f"blocked destructive command: {cmd!r}")
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(cwd)}
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=str(cwd), env=env, capture_output=True,
            text=True, timeout=timeout_s,
        )
        return proc.returncode, (proc.stdout + proc.stderr)[:8000]
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout_s}s"


def _safe_join(ws: Path, rel: str) -> Path:
    target = (ws / rel).resolve()
    if not str(target).startswith(str(ws.resolve())):
        raise ValueError(f"path escapes workspace: {rel}")
    return target


def build_tools(ws: Workspace, trajectory: Trajectory, full_surface: bool = False) -> list:
    from langchain_core.tools import StructuredTool

    allowed = {"read", "write", "create", "delete", "list", "execute"} if full_surface else ws.actions
    tools: list = []

    def _record(name: str, args: dict, output: str, exit_code: int | None = None) -> str:
        trajectory.add(TrajectoryEvent(kind="tool", name=name, args=args, output=output[:2000]))
        return output

    if "read" in allowed:
        def read_file(path: str) -> str:
            try:
                return _record("read_file", {"path": path},
                               _safe_join(ws.path, path).read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                return _record("read_file", {"path": path}, f"error: {e}")
        tools.append(StructuredTool.from_function(
            read_file, name="read_file", description="Read a file from the workspace."))

    if "list" in allowed:
        def list_dir(path: str = ".") -> str:
            try:
                base = _safe_join(ws.path, path)
                return _record("list_dir", {"path": path},
                               "\n".join(sorted(p.name for p in base.iterdir())))
            except Exception as e:
                return _record("list_dir", {"path": path}, f"error: {e}")
        tools.append(StructuredTool.from_function(
            list_dir, name="list_dir", description="List a directory in the workspace."))

    if {"write", "create"} & allowed:
        def write_file(path: str, content: str) -> str:
            try:
                target = _safe_join(ws.path, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return _record("write_file", {"path": path}, f"wrote {len(content)} bytes")
            except Exception as e:
                return _record("write_file", {"path": path}, f"error: {e}")
        tools.append(StructuredTool.from_function(
            write_file, name="write_file", description="Write a file in the workspace."))

    if "execute" in allowed:
        def run_command_tool(command: str) -> str:
            try:
                code, out = run_command(command, ws.path)
            except DestructiveCommandError as e:
                ws.violations.append(str(e))
                return f"refused: {e}"
            trajectory.add(TrajectoryEvent(kind="command", name=command, output=out[:2000],
                                           exit_code=code))
            return f"exit={code}\n{out}"
        tools.append(StructuredTool.from_function(
            run_command_tool, name="run_command",
            description="Run a shell command in the workspace."))

    # Record a violation if the agent will be denied a capability the skill needs.
    # (The agent simply won't have the tool; this note surfaces the gap in the report.)
    for needed in ("execute", "write"):
        if needed not in allowed and not full_surface:
            ws.violations  # no-op placeholder; real violations recorded at call sites above
    return tools
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_sandbox.py -q`
Expected: PASS. (Requires the `eval` extra installed: `pip install -e 'sdks/python[eval,test]'`.)

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/sandbox.py sdks/python/tests/test_evaluation_sandbox.py
git commit -m "feat(eval): add permission-scoped sandbox with workspace + shell deny-list

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Agent runner — tool-calling loop with step cap

**Files:**
- Create: `sdks/python/skill_sdk/evaluation/agent_exec.py`
- Test: `sdks/python/tests/test_evaluation_agent_exec.py`

**Interfaces:**
- Consumes: `Workspace`, `build_tools` (sandbox); `RunResult`, `Trajectory` (trajectory); `FakeToolCallingChatModel` in tests.
- Produces: `run_agent(prompt: str, ws: Workspace, model, *, skill_body: str | None = None, full_surface: bool = False, step_cap: int = 12) -> RunResult`. Runs a manual tool-calling loop: build tools, `model.bind_tools(tools)`, seed messages (system with `skill_body` if provided, else a bare assistant), loop until the model returns no tool calls or `step_cap` is hit, executing each tool call and feeding back `ToolMessage`s. Accumulates `usage_metadata` token counts into the trajectory. Returns a `RunResult` (never raises — captures errors into `RunResult.error`).

- [ ] **Step 1: Write the failing test**

```python
# sdks/python/tests/test_evaluation_agent_exec.py
from _fake_chat_model import FakeToolCallingChatModel
from langchain_core.messages import AIMessage

from skill_sdk.evaluation.agent_exec import run_agent
from skill_sdk.evaluation.sandbox import make_workspace

PERMS = [{"resource": "workspace", "actions": ["read", "write", "create", "list"]}]


def test_run_agent_executes_tool_then_finishes():
    ws = make_workspace(PERMS)
    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "write_file", "args": {"path": "out.txt", "content": "hi"}, "id": "1"}]),
        AIMessage(content="done"),
    ])
    res = run_agent("create out.txt", ws, model, skill_body="Always write out.txt.")
    assert res.error is None
    assert (ws.path / "out.txt").read_text() == "hi"
    assert res.final_text == "done"
    assert any(e.name == "write_file" for e in res.trajectory.events)


def test_run_agent_respects_step_cap():
    ws = make_workspace(PERMS)
    # model keeps requesting tools forever; step_cap must stop it
    looping = [AIMessage(content="", tool_calls=[
        {"name": "list_dir", "args": {"path": "."}, "id": str(i)}]) for i in range(50)]
    model = FakeToolCallingChatModel(responses=looping)
    res = run_agent("loop", ws, model, step_cap=3)
    assert res.error is not None
    assert "step cap" in res.error.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_agent_exec.py -q`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `agent_exec.py`**

```python
from __future__ import annotations

from .sandbox import Workspace, build_tools
from .trajectory import RunResult, Trajectory


def _system_text(skill_body: str | None) -> str:
    if skill_body:
        return (
            "You are an agent completing a task by following the skill instructions below. "
            "Use the provided tools to do real work in the workspace.\n\n"
            "=== SKILL INSTRUCTIONS ===\n" + skill_body
        )
    return (
        "You are an agent completing a task. Use the provided tools to do real work "
        "in the workspace."
    )


def run_agent(
    prompt: str,
    ws: Workspace,
    model,
    *,
    skill_body: str | None = None,
    full_surface: bool = False,
    step_cap: int = 12,
) -> RunResult:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    traj = Trajectory()
    result = RunResult(workspace_path=str(ws.path), trajectory=traj)
    try:
        tools = build_tools(ws, traj, full_surface=full_surface)
        tools_by_name = {t.name: t for t in tools}
        bound = model.bind_tools(tools) if tools else model
        messages = [SystemMessage(_system_text(skill_body)), HumanMessage(prompt)]

        for _ in range(step_cap):
            ai: AIMessage = bound.invoke(messages)
            messages.append(ai)
            usage = getattr(ai, "usage_metadata", None) or {}
            traj.tokens_in += usage.get("input_tokens", 0)
            traj.tokens_out += usage.get("output_tokens", 0)
            tool_calls = getattr(ai, "tool_calls", None) or []
            if not tool_calls:
                result.final_text = ai.content if isinstance(ai.content, str) else str(ai.content)
                result.permission_violations = ws.violations
                return result
            for call in tool_calls:
                name = call["name"]
                tool = tools_by_name.get(name)
                if tool is None:
                    ws.violations.append(f"agent attempted undeclared capability '{name}'")
                    out = f"error: tool '{name}' not available (permission not declared)"
                else:
                    out = tool.invoke(call["args"])
                messages.append(ToolMessage(content=str(out), tool_call_id=call["id"]))

        result.error = f"step cap ({step_cap}) reached without completion"
        result.permission_violations = ws.violations
        return result
    except Exception as e:  # never let a run crash the suite
        result.error = f"{type(e).__name__}: {e}"
        result.permission_violations = ws.violations
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_agent_exec.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/agent_exec.py sdks/python/tests/test_evaluation_agent_exec.py
git commit -m "feat(eval): add agent runner tool-calling loop with step cap

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Baseline orchestration + delta + judge

**Files:**
- Create: `sdks/python/skill_sdk/evaluation/baseline.py`
- Test: `sdks/python/tests/test_evaluation_baseline.py`

**Interfaces:**
- Consumes: `run_agent` (agent_exec), `make_workspace`/`cleanup` (sandbox), `evaluate_assertions` (assertions), `AgentExecutionSummary`/`ConfigAggregate` (state, Task 7). Imports `_build_model` from `.graph` for the default model path.
- Produces:
  - `find_previous_version(registry_path: Path, name: str, current_version: str) -> Path | None` — scans `registry_path/skills/<name>-<ver>` dirs, returns the SemVer-max strictly below `current_version`, else `None`.
  - `judge_run(model, case: dict, result: RunResult) -> dict` — asks the model for `{"llm_assertions": [{"statement","passed","evidence"}], "rubric_score": int|null}` over a workspace+trajectory summary; tolerant JSON parse; returns `{}` on failure.
  - `run_agent_execution(skill_path: Path, manifest: dict, registry_path: Path, task_cases: list[dict], model, *, default_runs: int = 1, keep_artifacts: bool = False) -> AgentExecutionSummary`.

- [ ] **Step 1: Write the failing tests**

```python
# sdks/python/tests/test_evaluation_baseline.py
import json
import tempfile
from pathlib import Path

from _fake_chat_model import FakeToolCallingChatModel
from langchain_core.messages import AIMessage

from skill_sdk.evaluation.baseline import find_previous_version, run_agent_execution

MANIFEST = {"name": "demo", "version": "1.1.0",
            "permissions": [{"resource": "ws", "actions": ["read", "write", "create", "list"]}]}


def _skill(tmp: Path, body: str = "Write out.txt with the answer.") -> Path:
    (tmp / "SKILL.md").write_text(f"---\nname: demo\nversion: 1.1.0\n---\n{body}")
    return tmp


def test_find_previous_version_picks_semver_max_below_current():
    reg = Path(tempfile.mkdtemp())
    skills = reg / "skills"
    for v in ("0.9.0", "1.0.0", "1.0.5", "1.1.0"):
        (skills / f"demo-{v}").mkdir(parents=True)
    prev = find_previous_version(reg, "demo", "1.1.0")
    assert prev is not None and prev.name == "demo-1.0.5"


def test_run_agent_execution_with_without_computes_delta():
    skill = _skill(Path(tempfile.mkdtemp()))
    reg = Path(tempfile.mkdtemp())  # no prior version -> with_without
    case = {"id": "c1", "input": {"type": "task", "prompt": "produce out.txt"},
            "expect": {"mode": "assertions",
                       "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}

    # with-skill writes the file (passes); baseline does nothing (fails)
    def fresh_model():
        return FakeToolCallingChatModel(responses=[
            AIMessage(content="", tool_calls=[
                {"name": "write_file", "args": {"path": "out.txt", "content": "x"}, "id": "1"}]),
            AIMessage(content="done"),
            AIMessage(content="I won't do it"),  # baseline run: no tool call
        ])

    summary = run_agent_execution(skill, MANIFEST, reg, [case], fresh_model())
    assert summary.comparison_mode == "with_without"
    assert summary.with_skill.pass_rate_mean == 1.0
    assert summary.baseline.pass_rate_mean == 0.0
    assert summary.delta["pass_rate"] == 1.0


def test_judge_run_parses_rubric_and_llm_assertions():
    from skill_sdk.evaluation.baseline import judge_run
    from skill_sdk.evaluation.trajectory import RunResult
    model = FakeToolCallingChatModel(responses=[AIMessage(content=json.dumps({
        "llm_assertions": [{"statement": "clean", "passed": True, "evidence": "tidy"}],
        "rubric_score": 80,
    }))])
    case = {"expect": {"assertions": [{"kind": "llm", "statement": "clean"}],
                       "rubric": "is it clean?"}}
    out = judge_run(model, case, RunResult(final_text="ok"))
    assert out["rubric_score"] == 80
    assert out["llm_assertions"][0]["passed"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_baseline.py -q`
Expected: FAIL — module does not exist (and `AgentExecutionSummary` not yet defined; Task 7 adds it, but write Task 7 first if executing strictly in order — see note).

> **Ordering note:** Task 6 imports `AgentExecutionSummary`/`ConfigAggregate` from `state.py`. If executing strictly top-to-bottom, do **Task 7 before Task 6** (or define the two dataclasses as the first step of Task 6 and delete the duplicate when reaching Task 7). Recommended: implement Task 7's dataclasses first, then return here.

- [ ] **Step 3: Implement `baseline.py`**

```python
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from ..validation import find_manifest_file, load_manifest
from .agent_exec import run_agent
from .assertions import evaluate_assertions
from .sandbox import cleanup, make_workspace
from .state import AgentExecutionSummary, ConfigAggregate
from .trajectory import RunResult


def _skill_body(skill_path: Path) -> str:
    """The Markdown body of SKILL.md (instructions the agent must follow)."""
    mp = find_manifest_file(skill_path)
    if mp is None or mp.name != "SKILL.md":
        return ""
    text = mp.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text


def find_previous_version(registry_path: Path, name: str, current_version: str) -> Path | None:
    from ..versioning import is_semver

    skills_dir = Path(registry_path) / "skills"
    if not skills_dir.exists():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for d in skills_dir.iterdir():
        if not d.is_dir() or not d.name.startswith(f"{name}-"):
            continue
        ver = d.name[len(name) + 1:]
        if not is_semver(ver):
            continue
        key = tuple(int(x) for x in ver.split("+")[0].split("-")[0].split("."))
        cur = tuple(int(x) for x in current_version.split("+")[0].split("-")[0].split("."))
        if key < cur:
            candidates.append((key, d))
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[0])[1]


def _workspace_summary(result: RunResult) -> str:
    ws = Path(result.workspace_path) if result.workspace_path else None
    files = []
    if ws and ws.exists():
        for p in sorted(ws.rglob("*")):
            if p.is_file() and "node_modules" not in p.parts:
                files.append(str(p.relative_to(ws)))
    cmds = [e.name for e in result.trajectory.commands()]
    return f"files={files[:40]}\ncommands={cmds[:40]}\nfinal_text={result.final_text[:1000]}"


def judge_run(model, case: dict[str, Any], result: RunResult) -> dict[str, Any]:
    llm_asserts = [a for a in case.get("expect", {}).get("assertions", []) if a.get("kind") == "llm"]
    rubric = case.get("expect", {}).get("rubric")
    if not llm_asserts and not rubric:
        return {}
    statements = [a.get("statement", "") for a in llm_asserts]
    prompt = (
        "Grade this agent run. Respond ONLY with JSON: "
        '{"llm_assertions":[{"statement":str,"passed":bool,"evidence":str}],'
        '"rubric_score":int|null}.\n'
        f"Statements to grade: {json.dumps(statements)}\n"
        f"Holistic rubric (0-100, null if none): {json.dumps(rubric)}\n\n"
        f"Run summary:\n{_workspace_summary(result)}"
    )
    try:
        from langchain_core.messages import HumanMessage

        ai = model.invoke([HumanMessage(prompt)])
        text = ai.content if isinstance(ai.content, str) else str(ai.content)
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1]) if start != -1 else {}
    except Exception:
        return {}


def _aggregate(per_run_pass: list[float], tokens: list[int], durations: list[int]) -> ConfigAggregate:
    def _ms(xs):  # mean+stddev helper
        return (statistics.fmean(xs) if xs else 0.0,
                statistics.pstdev(xs) if len(xs) > 1 else 0.0)
    pr_m, pr_s = _ms(per_run_pass)
    tk_m, tk_s = _ms(tokens)
    du_m, du_s = _ms(durations)
    return ConfigAggregate(
        pass_rate_mean=pr_m, pass_rate_stddev=pr_s,
        tokens_mean=tk_m, tokens_stddev=tk_s,
        duration_mean=du_m, duration_stddev=du_s,
    )


def _run_one(skill_path, body, permissions, case, model, *, full_surface, keep):
    ws = make_workspace(permissions, files=case.get("input", {}).get("files"),
                        skill_path=skill_path)
    try:
        res = run_agent(case["input"]["prompt"], ws, model,
                        skill_body=None if full_surface else body, full_surface=full_surface)
        typed = evaluate_assertions(case, res, input_files=ws.input_files)
        judged = judge_run(model, case, res)
        llm_results = judged.get("llm_assertions", [])
        all_results = typed + [
            {"kind": "llm", "passed": bool(r.get("passed")), "evidence": r.get("evidence", "")}
            for r in llm_results
        ]
        # permission violation forces this run to 0
        if res.permission_violations:
            pass_rate = 0.0
        elif all_results:
            pass_rate = sum(1 for r in all_results if r["passed"]) / len(all_results)
        else:
            pass_rate = 0.0
        return {
            "pass_rate": pass_rate,
            "tokens": res.trajectory.tokens_in + res.trajectory.tokens_out,
            "duration": res.trajectory.duration_ms,
            "assertions": all_results,
            "rubric_score": judged.get("rubric_score"),
            "violations": res.permission_violations,
            "error": res.error,
        }
    finally:
        cleanup(ws, keep=keep)


def run_agent_execution(
    skill_path: Path,
    manifest: dict[str, Any],
    registry_path: Path,
    task_cases: list[dict[str, Any]],
    model,
    *,
    default_runs: int = 1,
    keep_artifacts: bool = False,
) -> AgentExecutionSummary:
    permissions = manifest.get("permissions", [])
    body = _skill_body(skill_path)
    name = manifest.get("name", skill_path.name)
    version = manifest.get("version", "0.0.0")

    prev = find_previous_version(registry_path, name, version)
    mode = "vs_previous" if prev else "with_without"
    prev_body = _skill_body(prev) if prev else ""
    prev_perms = []
    if prev:
        mp = find_manifest_file(prev)
        if mp:
            try:
                prev_perms = load_manifest(mp).get("permissions", [])
            except Exception:
                prev_perms = []

    runs_per_case = max((c.get("runs", default_runs) for c in task_cases), default=default_runs)
    with_pass, with_tok, with_dur = [], [], []
    base_pass, base_tok, base_dur = [], [], []
    case_reports = []

    for case in task_cases:
        n = case.get("runs", default_runs)
        cw, cb = [], []
        for _ in range(n):
            w = _run_one(skill_path, body, permissions, case, model,
                         full_surface=False, keep=keep_artifacts)
            with_pass.append(w["pass_rate"]); with_tok.append(w["tokens"]); with_dur.append(w["duration"])
            cw.append(w)
            if mode == "vs_previous":
                b = _run_one(prev, prev_body, prev_perms, case, model,
                             full_surface=False, keep=keep_artifacts)
            else:
                b = _run_one(skill_path, "", permissions, case, model,
                             full_surface=True, keep=keep_artifacts)
            base_pass.append(b["pass_rate"]); base_tok.append(b["tokens"]); base_dur.append(b["duration"])
            cb.append(b)
        case_reports.append({"case_id": case["id"], "with_skill": cw, "baseline": cb})

    with_agg = _aggregate(with_pass, with_tok, with_dur)
    base_agg = _aggregate(base_pass, base_tok, base_dur)
    delta = {
        "pass_rate": round(with_agg.pass_rate_mean - base_agg.pass_rate_mean, 4),
        "tokens": round(with_agg.tokens_mean - base_agg.tokens_mean, 1),
        "duration": round(with_agg.duration_mean - base_agg.duration_mean, 1),
    }
    return AgentExecutionSummary(
        comparison_mode=mode, skip_reason=None, runs_per_case=runs_per_case,
        with_skill=with_agg, baseline=base_agg, delta=delta, cases=case_reports,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_baseline.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/baseline.py sdks/python/tests/test_evaluation_baseline.py
git commit -m "feat(eval): add baseline orchestration, delta, and judge for agent execution

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Report dataclasses + scoring integration

> **Execute this before Task 6** (or define these two dataclasses first inside Task 6). See Task 6 ordering note.

**Files:**
- Modify: `sdks/python/skill_sdk/evaluation/state.py`
- Test: `sdks/python/tests/test_evaluation_state.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `ConfigAggregate(pass_rate_mean, pass_rate_stddev, tokens_mean, tokens_stddev, duration_mean, duration_stddev)` (all `float`, default `0.0`) with `to_dict()`.
  - `AgentExecutionSummary(comparison_mode: str, skip_reason: str | None, runs_per_case: int, with_skill: ConfigAggregate, baseline: ConfigAggregate, delta: dict, cases: list[dict])` with `to_dict()`.
  - `EvaluationReport` gains `agent_execution: AgentExecutionSummary | None = None`; `to_dict()` emits an `agent_execution` key (its `to_dict()` or `None`).
  - `compute_overall_score(report) -> float | None` helper: mean of available components — `test_score` (`100*passed/total` when total), `content_score` (`100 - severity penalty`), `agent_exec_score` (`100 * with_skill.pass_rate_mean` when `agent_execution` present and not skipped).

- [ ] **Step 1: Write the failing tests**

```python
# append to sdks/python/tests/test_evaluation_state.py
from skill_sdk.evaluation.state import (
    AgentExecutionSummary,
    ConfigAggregate,
    EvaluationReport,
)


def _report():
    return EvaluationReport(skill_name="s", skill_version="1.0.0", run_at="t",
                            judge_status="ok", judge_skip_reason=None)


def test_report_to_dict_has_agent_execution_none_by_default():
    assert _report().to_dict()["agent_execution"] is None


def test_agent_execution_summary_serializes():
    summ = AgentExecutionSummary(
        comparison_mode="with_without", skip_reason=None, runs_per_case=1,
        with_skill=ConfigAggregate(pass_rate_mean=1.0),
        baseline=ConfigAggregate(pass_rate_mean=0.0),
        delta={"pass_rate": 1.0, "tokens": 50.0, "duration": 10.0}, cases=[])
    r = _report()
    r.agent_execution = summ
    d = r.to_dict()["agent_execution"]
    assert d["comparison_mode"] == "with_without"
    assert d["with_skill"]["pass_rate_mean"] == 1.0
    assert d["delta"]["pass_rate"] == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_state.py -q`
Expected: FAIL — `ConfigAggregate`/`AgentExecutionSummary` not defined.

- [ ] **Step 3: Implement the dataclasses + wire into `EvaluationReport`**

```python
# add to sdks/python/skill_sdk/evaluation/state.py (above EvaluationReport)
@dataclass
class ConfigAggregate:
    pass_rate_mean: float = 0.0
    pass_rate_stddev: float = 0.0
    tokens_mean: float = 0.0
    tokens_stddev: float = 0.0
    duration_mean: float = 0.0
    duration_stddev: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate_mean": self.pass_rate_mean,
            "pass_rate_stddev": self.pass_rate_stddev,
            "tokens_mean": self.tokens_mean,
            "tokens_stddev": self.tokens_stddev,
            "duration_mean": self.duration_mean,
            "duration_stddev": self.duration_stddev,
        }


@dataclass
class AgentExecutionSummary:
    comparison_mode: str  # "with_without" | "vs_previous" | "skipped"
    skip_reason: str | None
    runs_per_case: int
    with_skill: ConfigAggregate = field(default_factory=ConfigAggregate)
    baseline: ConfigAggregate = field(default_factory=ConfigAggregate)
    delta: dict[str, Any] = field(default_factory=dict)
    cases: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_mode": self.comparison_mode,
            "skip_reason": self.skip_reason,
            "runs_per_case": self.runs_per_case,
            "with_skill": self.with_skill.to_dict(),
            "baseline": self.baseline.to_dict(),
            "delta": self.delta,
            "cases": self.cases,
        }
```

Add the field to `EvaluationReport` (after `test_executor`):

```python
    agent_execution: "AgentExecutionSummary | None" = None
```

Add to `EvaluationReport.to_dict()` (before `"overall_score"`):

```python
            "agent_execution": self.agent_execution.to_dict() if self.agent_execution else None,
```

Append the scoring helper at module end:

```python
_SEVERITY_WEIGHT = {"error": 20, "warning": 10, "info": 2}


def compute_overall_score(report: "EvaluationReport") -> float | None:
    components: list[float] = []
    te = report.test_executor
    if te.total:
        components.append(100.0 * te.passed / te.total)
    if report.content_critic_findings:
        penalty = sum(_SEVERITY_WEIGHT.get(f.get("severity", "info"), 2)
                      for f in report.content_critic_findings)
        components.append(max(0.0, 100.0 - penalty))
    ae = report.agent_execution
    if ae and ae.comparison_mode != "skipped":
        components.append(100.0 * ae.with_skill.pass_rate_mean)
    return round(sum(components) / len(components), 2) if components else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sdks/python && python -m pytest tests/test_evaluation_state.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/state.py sdks/python/tests/test_evaluation_state.py
git commit -m "feat(eval): add agent-execution report dataclasses and overall-score helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Wire agent-execution into `evaluate_skill`

**Files:**
- Modify: `sdks/python/skill_sdk/evaluation/__init__.py`
- Modify: `sdks/python/skill_sdk/evaluation/graph.py` (export `_build_model` usage is already importable; no change needed unless re-exporting)
- Modify: `sdks/python/skill_sdk/validation.py` (add the execute-missing warning in `lint_full_skill`)
- Test: `sdks/python/tests/test_evaluation.py`

**Interfaces:**
- Consumes: `run_agent_execution` (baseline), `_build_model` (graph), `compute_overall_score` (state).
- Produces: `evaluate_skill` now runs the agent-execution pass when task cases exist and a model is available; sets `report.agent_execution` and recomputes `overall_score`. New private helper `_split_task_cases(eval_cases) -> tuple[list, list]` returning `(non_task_cases, task_cases)`.

- [ ] **Step 1: Write the failing tests**

```python
# append to sdks/python/tests/test_evaluation.py
import json
import tempfile
from pathlib import Path

from skill_sdk.evaluation import evaluate_skill


def _skill_with_task(tmp: Path):
    (tmp / "src").mkdir(parents=True)
    (tmp / "src" / "main.py").write_text("# placeholder")
    (tmp / "SKILL.md").write_text(
        "---\nname: demo\nversion: 1.0.0\nruntime: python\napi_version: 1\n"
        "entry: src/main.py\ndescription: A demo skill for when you need a demo\n"
        "permissions:\n  - resource: ws\n    actions: [read, write, create, list]\n---\n"
        "Write out.txt containing the answer.")
    (tmp / "tests").mkdir(exist_ok=True)
    (tmp / "tests" / "eval_cases.yaml").write_text(json.dumps({"version": 1, "cases": [
        {"id": "c1", "input": {"type": "task", "prompt": "produce out.txt"},
         "expect": {"mode": "assertions",
                    "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}]}))
    return tmp


def test_evaluate_skill_skips_agent_execution_without_model(monkeypatch):
    monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
    skill = _skill_with_task(Path(tempfile.mkdtemp()))
    report = evaluate_skill(skill, judge="none")
    # judge none -> agent execution skipped, not crashed
    assert report.agent_execution is None or report.agent_execution.comparison_mode == "skipped"
    assert report.judge_status == "skipped"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sdks/python && python -m pytest tests/test_evaluation.py -q`
Expected: FAIL — `report.agent_execution` attribute access or skip handling not yet wired (depending on prior task state). If it errors on the unknown `task` input type during deterministic execution, that confirms wiring is needed.

- [ ] **Step 3: Wire it in**

In `evaluate_skill`, after loading `eval_cases`, split out task cases so the deterministic harness pass never receives them (the harness has no `task` handler):

```python
    eval_cases = ...  # existing
    non_task_cases, task_cases = _split_task_cases(eval_cases)
```

Use `non_task_cases` for `ExecutorSummary(total=...)` and `_run_deterministic_cases`. Add the helper:

```python
def _split_task_cases(
    eval_cases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    task = [c for c in eval_cases if c.get("input", {}).get("type") == "task"]
    non_task = [c for c in eval_cases if c.get("input", {}).get("type") != "task"]
    return non_task, task
```

Add an agent-execution pass. For `judge == "none"` or when no model is available, set a skipped summary. Insert before/around the existing judge handling:

```python
    from .state import AgentExecutionSummary, ConfigAggregate, compute_overall_score

    def _skipped_ae(reason: str) -> AgentExecutionSummary:
        return AgentExecutionSummary(comparison_mode="skipped", skip_reason=reason,
                                     runs_per_case=0, with_skill=ConfigAggregate(),
                                     baseline=ConfigAggregate(), delta={}, cases=[])

    if task_cases:
        if judge == "none":
            report.agent_execution = _skipped_ae("judge explicitly disabled (--judge none)")
        else:
            try:
                from .baseline import run_agent_execution
                from .graph import _build_model
                model = _build_model(judge)
                if model is None:
                    report.agent_execution = _skipped_ae(
                        "no judge model configured (set SKILLS_EVAL_MODEL or --judge)")
                else:
                    report.agent_execution = run_agent_execution(
                        skill_path, manifest, registry_path, task_cases, model)
            except ImportError:
                report.agent_execution = _skipped_ae(
                    "evaluation agents unavailable (install skill_sdk[eval])")
            except Exception as e:
                report.agent_execution = _skipped_ae(f"agent execution error: {e}")

    report.overall_score = compute_overall_score(report)
```

Ensure this runs on all return paths (the `judge == "none"` early return and the `ImportError` early return must also set `agent_execution` + recompute `overall_score` before returning). Simplest: compute the agent-execution block and `overall_score` **before** the existing judge-none / import-guard returns, then let those returns proceed; have `run_agentic_evaluation` preserve `base_report.agent_execution` (it already returns the same report object it receives via `base_report`).

Add the execute-permission lint warning in `validation.py:lint_full_skill` (so authors see it at validate time):

```python
    # in lint_full_skill, after loading manifest + eval cases
    try:
        from .evaluation.cases import load_eval_cases
        cases = load_eval_cases(skill_path)
    except Exception:
        cases = []
    declared = {a for p in (manifest.get("permissions") or []) for a in p.get("actions", [])}
    for c in cases:
        if c.get("input", {}).get("type") != "task":
            continue
        kinds = {a.get("kind") for a in c.get("expect", {}).get("assertions", [])}
        if ({"command_ran", "exit_code"} & kinds) and "execute" not in declared:
            warnings.append(
                f"case '{c.get('id')}': uses command_ran/exit_code but skill declares no "
                "'execute' permission — those assertions can never pass")
```

(Adapt `warnings`/`manifest` variable names to the actual `lint_full_skill` body.)

- [ ] **Step 4: Run the full eval suite**

Run: `cd sdks/python && python -m pytest tests/test_evaluation.py tests/test_evaluation_cases.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sdks/python/skill_sdk/evaluation/__init__.py sdks/python/skill_sdk/validation.py sdks/python/tests/test_evaluation.py
git commit -m "feat(eval): run agent-execution pass in evaluate_skill with graceful skip

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: CLI rendering + `--keep-artifacts`

**Files:**
- Modify: `cli/src/main.py` (the `evaluate` command + its markdown renderer)
- Test: `cli/tests/test_cli.py`

**Interfaces:**
- Consumes: the serialized report's new `agent_execution` block.
- Produces: markdown output includes an "Agent execution" section (comparison mode, with/baseline pass-rate, delta) when present; `--keep-artifacts` flag is accepted and threaded to the evaluation (passed through to `run_agent_execution(..., keep_artifacts=True)` — requires adding a `keep_artifacts` param to `evaluate_skill` and forwarding it).

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_cli.py — a markdown-rendering unit test that doesn't need a model
def test_evaluate_markdown_renders_agent_execution_section(capsys):
    from skill_sdk.evaluation.state import (
        AgentExecutionSummary, ConfigAggregate, EvaluationReport)
    # import the renderer used by cmd_evaluate (adjust name to the actual function)
    from cli.src.main import _render_eval_markdown  # noqa
    report = EvaluationReport(skill_name="s", skill_version="1.0.0", run_at="t",
                              judge_status="ok", judge_skip_reason=None)
    report.agent_execution = AgentExecutionSummary(
        comparison_mode="with_without", skip_reason=None, runs_per_case=1,
        with_skill=ConfigAggregate(pass_rate_mean=0.9),
        baseline=ConfigAggregate(pass_rate_mean=0.3),
        delta={"pass_rate": 0.6, "tokens": 1200.0, "duration": 8000.0}, cases=[])
    text = _render_eval_markdown(report)
    assert "Agent execution" in text
    assert "with_without" in text
    assert "0.6" in text  # delta pass_rate
```

> If the CLI currently renders inline in `cmd_evaluate` rather than a helper, the first sub-step is to **extract** the markdown rendering into `_render_eval_markdown(report) -> str` (pure, returns a string `cmd_evaluate` prints), then add the section. This keeps it testable without spawning the process.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=sdks/python python -m pytest cli/tests/test_cli.py -q` (from repo root)
Expected: FAIL — `_render_eval_markdown` missing or no agent-execution section.

- [ ] **Step 3: Implement**

Extract/extend the renderer to append:

```python
    ae = report.agent_execution
    if ae is not None:
        lines.append("  Agent execution:")
        if ae.comparison_mode == "skipped":
            lines.append(f"    skipped: {ae.skip_reason}")
        else:
            lines.append(f"    mode: {ae.comparison_mode} (runs/case: {ae.runs_per_case})")
            lines.append(f"    with-skill pass-rate: {ae.with_skill.pass_rate_mean:.2f}"
                         f" (±{ae.with_skill.pass_rate_stddev:.2f})")
            lines.append(f"    baseline pass-rate:   {ae.baseline.pass_rate_mean:.2f}"
                         f" (±{ae.baseline.pass_rate_stddev:.2f})")
            d = ae.delta
            lines.append(f"    delta: pass-rate {d.get('pass_rate')}, "
                         f"tokens {d.get('tokens')}, duration_ms {d.get('duration')}")
```

Add the `--keep-artifacts` argument to the `evaluate` subparser and forward it: add `keep_artifacts: bool = False` to `evaluate_skill(...)` and pass through to `run_agent_execution(..., keep_artifacts=keep_artifacts)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=sdks/python python -m pytest cli/tests/test_cli.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cli/src/main.py cli/tests/test_cli.py sdks/python/skill_sdk/evaluation/__init__.py
git commit -m "feat(cli): render agent-execution section and add --keep-artifacts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: API passthrough test + docs

**Files:**
- Test: `frontend/api/tests/test_evaluation_routes.py`
- Modify: `docs/` — add a section to the testing/evaluation doc (find with `grep -rl "evaluation" docs`) describing task cases + the pragmatic-sandbox safety warning.

**Interfaces:**
- Consumes: the run endpoint's existing `.to_dict()` serialization (already returns the whole report).
- Produces: a test asserting the `agent_execution` key is present in the run-endpoint response (skipped mode is fine without a model); a docs section.

- [ ] **Step 1: Write the failing test**

```python
# append to frontend/api/tests/test_evaluation_routes.py
def test_run_endpoint_includes_agent_execution_key(client, published_skill_with_task_case):
    # published_skill_with_task_case: fixture that publishes a skill whose
    # eval_cases.yaml has one task case (mirror existing publish fixtures).
    resp = client.post(f"/api/skills/{published_skill_with_task_case}/evaluation/run",
                       json={"judge": "none"}, headers=_api_key_header())
    assert resp.status_code == 200
    body = resp.json()
    assert "agent_execution" in body  # present, skipped (no model under --judge none)
```

> Reuse the existing publish/fixture and api-key helpers in the test module; if no task-case fixture exists, extend the closest existing one to add a single `task` case to its `eval_cases.yaml`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=sdks/python python -m pytest frontend/api/tests/test_evaluation_routes.py -q` (from repo root)
Expected: FAIL — `agent_execution` not in body (only if Task 7/8 not yet wired; if they are, this test should pass immediately, confirming passthrough — in which case keep it as a regression guard).

- [ ] **Step 3: Implement / confirm**

No route change is expected (the endpoint serializes the whole report). If the test fails because the report lacks the key, confirm Task 7's `to_dict()` change shipped. Then write the docs section:

```markdown
## Agent-execution eval (task cases)

A `task` case runs a real LLM agent that follows the skill's SKILL.md in a
temporary, permission-scoped workspace, then grades the workspace + trajectory
against a baseline (with/without skill, or vs the previous published version).

> **Safety:** the shell sandbox is *pragmatic*, not true isolation — commands run
> with the working directory locked to a temp workspace, a minimized environment,
> a timeout, and a destructive-pattern deny-list. A determined command could still
> affect the host. Only run agent-execution evals on skills you trust, or in a
> disposable/CI environment. Container-level isolation is a planned upgrade.
```

- [ ] **Step 4: Run the full test matrix**

Run: `make test`
Expected: PASS (Python SDK + CLI + skill + harness + TS). Then `make lint`.

- [ ] **Step 5: Commit**

```bash
git add frontend/api/tests/test_evaluation_routes.py docs
git commit -m "test(eval): assert agent_execution passthrough; document task cases + sandbox safety

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- §3 modules (sandbox/agent_exec/trajectory/assertions/baseline) → Tasks 2–6. ✓
- §4 case schema (task type, assertions mode, kinds, runs, baseline, validation incl. execute warning) → Task 1 + Task 8 (execute warning). ✓
- §5 runner & sandbox (permission→tool, workspace lifecycle, pragmatic shell, step cap) → Tasks 4, 5. ✓
- §6 baseline & delta (mode auto-select, fairness rule, aggregation, delta) → Task 6. ✓
- §7 report & scoring (ConfigAggregate, AgentExecutionSummary, overall_score) → Task 7. ✓
- §8 error handling/degradation (skip not error; per-run errors; try/finally cleanup; permission violation fails case) → Tasks 4–6, 8. ✓
- §9 testing (pure unit; fake-model; CLI/API integration) → every task + Tasks 9, 10. ✓
- §10 open considerations (sandbox warning documented) → Task 10 docs. ✓

**Placeholder scan:** No "TBD/TODO". The two "adapt variable names" notes (Task 8 lint warning, Task 9 renderer extraction) are deliberate integration instructions against existing code whose exact local names the implementer will read, not missing content.

**Type consistency:** `AgentExecutionSummary`/`ConfigAggregate` field names match between Task 6 (constructed in `baseline.py`), Task 7 (defined in `state.py`), Task 8 (skipped summary), and Tasks 9/10 (rendered/serialized). `RunResult`/`Trajectory`/`TrajectoryEvent` fields are consistent across Tasks 2–6. `evaluate_assertions(case, result, input_files=...)` signature matches its caller in Task 6. `run_agent(prompt, ws, model, *, skill_body, full_surface, step_cap)` matches Task 6's calls.

**Ordering caveat (explicit):** Task 7 must precede Task 6 (Task 6 imports from `state.py`). Flagged in both tasks.
