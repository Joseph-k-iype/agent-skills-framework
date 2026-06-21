# Agent-Execution Baseline Evaluation — Design

**Date:** 2026-06-22
**Status:** Approved (design); pending implementation plan
**Scope:** Feature "A" from the skills-eval research synthesis — add an agent-execution
eval mode with baseline comparison to `skill_sdk.evaluation`.

## 1. Motivation

The research (OpenAI/Codex eval guide, agentskills.io eval-driven iteration, and the
*Agent Skill Evaluation and Evolution* survey) converges on one thesis: **a skill is a
prompt artifact, and you evaluate it by running an agent that consumes it and grading what
actually happened, relative to a baseline.**

Our current `skill_sdk.evaluation` module tests the skill's **code** (the `BaseSkill`
`handle_command`/`handle_event` contract, via `testing/harness.py`) plus a static
content-critic that *reads* `SKILL.md`. Nothing ever runs an agent that **follows** the
instructions and verifies it succeeded, and nothing produces a **baseline** ("is this skill
worth it versus the bare model / the previous version?"). This feature closes that gap.

It also unlocks, as by-products, three things the research names as gaps: trajectory/outcome
checks, composite metrics (tokens + latency, reported as a delta), and a permission-regression
check.

## 2. Goals / Non-goals

**Goals**
- Run a real LLM agent that reads a skill's `SKILL.md` and performs a natural-language task
  in a sandbox, then grade the **workspace + trajectory** it produced.
- Always produce a **baseline delta**: with-skill vs without-skill (new skills) or
  with-skill vs previous-published-version (existing skills), auto-selected.
- Express success as **typed deterministic assertions + LLM-judged rubric**.
- Scope the agent's tool surface to the skill's declared `permissions` (default-deny),
  turning the eval into a **permission-regression** check for free.
- Capture **tokens, duration, tool/command trajectory**; support **N runs** per case for
  variance (default 1).
- Preserve the existing graceful-degradation contract: no model / no extras → skipped,
  never errored; deterministic results always preserved.

**Non-goals (deferred to later features B–F)**
- Trigger/routing evaluation (does the description fire at the right time).
- The auto-rewrite "evolution" loop.
- Downstream re-evaluation on change.
- Security-audit agent.
- Longitudinal trend charting.
- True OS-level / container isolation (see §5 — pragmatic sandbox only in v1).

## 3. Architecture

Approach: **extend the existing module additively.** All new code lives under
`sdks/python/skill_sdk/evaluation/`. Existing harness executor, content-critic,
test-executor, memory loop, and the CLI/API/UI surfaces are unchanged; the new
agent-execution results flow through the same `EvaluationReport` and sidecar storage.

### New modules

| File | Responsibility | Model-dependent? |
|---|---|---|
| `sandbox.py` | Temp-workspace lifecycle; permission→tool mapping (resource/actions → fs/shell tools), default-deny; pragmatic shell isolation. | No |
| `agent_exec.py` | The agent runner: build tool set, run the LangChain tool-calling loop with step cap + timeout, return `RunResult`. | Yes |
| `trajectory.py` | `Trajectory` dataclass + capture via LangChain callbacks (ordered tool/command events, tokens, duration, exit codes). | No |
| `assertions.py` | Typed deterministic checks evaluated against a `RunResult`. | No |
| `baseline.py` | Orchestrator: pick comparison mode from registry state; run both configs × N runs; aggregate mean/stddev; compute delta. | Yes |

### Changes to existing files

- `cases.py` — add `input.type: "task"` and `expect.mode: "assertions"`; new validation rules.
- `state.py` — add `AgentExecutionSummary` dataclass and an `agent_execution` field on
  `EvaluationReport`; extend `overall_score`.
- `__init__.py` (`evaluate_skill`) — after the deterministic harness pass, if any `task`
  cases exist **and** a model is available, call `baseline.run_agent_execution(...)`.
- CLI (`cli/src/main.py` `evaluate`) — render the new section in markdown/json output;
  add `--keep-artifacts` flag.
- API (`frontend/api/routes/evaluation.py`) — the run endpoint already serializes the full
  report via `.to_dict()`; the new section flows through automatically. UI rendering of the
  section is in-scope for the frontend but specced separately if needed.

### Data flow

```
evaluate_skill
 ├─ structural validate + lint            (existing)
 ├─ harness deterministic cases           (existing: command/event)
 ├─ agentic content-critic + test-exec    (existing: LangGraph)
 └─ agent_execution (NEW, if task cases present AND model available)
      └─ baseline.run_agent_execution:
           mode = vs_previous if prior published version else with_without
           for config in [with_skill, baseline]:
             for case in task_cases:
               for run in range(case.runs):
                 ws = sandbox.make_workspace(permissions, case.files)
                 res = agent_exec.run(prompt, tools, model, step_cap, timeout)  # -> RunResult
                 assertion_results = assertions.evaluate(case, res)
                 rubric_score      = judge_rubric(case, res)            # reuse judge model
                 record per-run pass_rate, tokens, duration, violations
           aggregate mean/stddev per config; delta = with_skill - baseline
```

Independent testability: `assertions`, `trajectory`, `sandbox` need no model; `agent_exec`
and `baseline` are the only model-dependent pieces and are driven by a scripted fake chat
model in tests.

## 4. Case schema

Task cases reuse the existing `id`/`description`/`input`/`expect` envelope. `command`/`event`
cases are unchanged.

```yaml
# tests/eval_cases.yaml
- id: scaffold-demo-app
  description: Skill should scaffold a working Vite+React+Tailwind app
  input:
    type: task                          # NEW (alongside command|event)
    prompt: "Set up a minimal React demo app with Tailwind for quick UI experiments"
    files:                              # optional: copied into the workspace before the run
      - tests/fixtures/sales_2025.csv
  expect:
    mode: assertions                    # NEW (alongside exact_match|contains|llm_judged)
    assertions:
      - { kind: command_ran,    pattern: "npm install" }
      - { kind: file_exists,    path: "package.json" }
      - { kind: file_exists,    path: "src/components/*.tsx" }      # glob
      - { kind: file_contains,  path: "src/index.css", text: '@import "tailwindcss"' }
      - { kind: exit_code,      command: "npm run build", equals: 0 }
      - { kind: no_extra_files, allow: ["node_modules/**", "dist/**"] }
      - { kind: llm, statement: "Components are functional and styled with Tailwind utility classes, no CSS modules" }
    rubric: "Overall, is this a clean, minimal, idiomatic demo app a developer would accept?"
  runs: 1            # optional case-level override of the default (1)
  baseline: auto     # optional: auto | with_without | vs_previous
```

### Typed assertion kinds (deterministic, `assertions.py`, no model)

| kind | params | check |
|---|---|---|
| `file_exists` | `path` (literal or glob) | ≥1 match exists in workspace |
| `file_contains` | `path`, `text` **or** `pattern` (regex) | a match's content contains text/regex |
| `command_ran` | `pattern` (substring or `/regex/`) | trajectory has a shell event matching it |
| `exit_code` | `command` (pattern, optional), `equals` (int) | matched command's exit code equals value; if `command` omitted, the last command |
| `no_extra_files` | `allow` (list of globs) | no workspace files beyond input files + allowlist (git-clean style) |

### LLM assertion + rubric

- `{kind: llm, statement: "..."}` — judged PASS/FAIL with quoted evidence by the judge agent
  over the workspace + trajectory.
- Case-level optional `rubric` — a separate holistic 0–100 score (the agentskills.io
  "blind quality" signal), distinct from the per-assertion pass/fail.

### Implicit permission assertion

The sandbox records any attempt to act outside the skill's declared `permissions`. A
violation is attached to the case result and **fails the case** — no assertion needed.

### `cases.py` validation additions

- `VALID_INPUT_TYPES` += `task`; `VALID_EXPECT_MODES` += `assertions`.
- `task` requires `input.prompt` (non-empty str); `input.files` (if present) must be a list
  of strings.
- `assertions` mode requires a non-empty `assertions` list; each entry needs a known `kind`
  and that kind's required params; unknown `kind` is an **error** (fail closed).
- `runs` (if present) must be a positive int; `baseline` (if present) ∈
  `{auto, with_without, vs_previous}`.
- **Warning** (not error): a case using `command_ran`/`exit_code` while the skill declares no
  `execute` permission — the assertion can never pass because the agent cannot run commands.

## 5. Runner & sandbox

### Permission → tool mapping (`sandbox.py`)

`permissions` is a list of `{resource: str, actions: [read|write|create|delete|list|execute]}`.

| declared action | tool(s) provided |
|---|---|
| `read` | `read_file` (workspace-scoped) |
| `list` | `list_dir` (workspace-scoped) |
| `write` / `create` / `delete` | `write_file` / `delete_file` (workspace-scoped) |
| `execute` | `run_command` |

- **Default-deny:** an action not declared → its tool is not provided. If the agent tries to
  use a missing capability, the attempt is logged as a `permission_violation`.
- Filesystem tools are chrooted to the temp workspace. Resource globs are matched **relative
  to the workspace**. Absolute/external resources are denied in v1 and noted in the result.

### Workspace lifecycle

- `make_workspace(permissions, files)`: `tempfile.mkdtemp`, copy `input.files` in, return a
  workspace handle with the scoped tool set.
- Cleanup in `try/finally`; workspace deleted unless `--keep-artifacts` (CLI) / a keep flag
  is set. (Future: artifacts could be persisted alongside sidecar reports.)

### Shell isolation (pragmatic, no new deps)

`run_command` executes with: `cwd` locked to the workspace; a minimized environment; a
wall-clock **timeout**; and a **deny-list** of obviously destructive/exfiltration patterns
(e.g. `rm -rf /`, `:(){ :|:& };:`, `curl ... | sh`, writes outside the workspace). This is
**not** OS-level isolation — a determined command could still escape. Acceptable for
trusted/first-party skills; documented with a loud warning. (Docker/`sandbox-exec` isolation
is a deliberate future upgrade, out of scope here.)

### Agent loop (`agent_exec.py`)

`run(prompt, tools, model, step_cap, timeout) -> RunResult`. A LangChain tool-calling loop
with a **step cap** and **wall-clock timeout** (both catch thrashing — the codex signal).
The skill's `SKILL.md` body is injected into the agent context for the `with_skill` config.
Trajectory captured via callbacks.

`RunResult`: `{ final_text, workspace_path, trajectory, permission_violations, error }`.
`Trajectory`: ordered events `[{kind: tool|command, name/command, args, output, exit_code}]`
+ `tokens_in`, `tokens_out`, `duration_ms`.

## 6. Baseline & delta (`baseline.py`)

- **Mode auto-select:** prior published version exists in the registry → `vs_previous`
  (snapshot its `SKILL.md` into a temp skill dir; run with *its* instructions + permissions);
  else `with_without`. A case-level `baseline:` overrides. `vs_previous` with prior source
  unavailable → fall back to `with_without` with a note.
- **Fairness rule:** the `baseline` (without-skill / previous-version) config and the
  `with_skill` config get the **same prompt**. For `with_without`, the without-skill config
  gets a *default* tool surface (filesystem + sandboxed shell) so the delta isolates the
  **instructions'** value, not merely the granting of tools.
- **Aggregation:** per config, per case, per run → per-run `pass_rate` = fraction of
  assertions passed (permission violation forces 0 for that run). Across runs → `mean` +
  `stddev` of pass_rate, tokens, duration.
- **Delta:** `delta = with_skill.mean − baseline.mean` for pass_rate, tokens, duration.

## 7. Report & scoring (`state.py`)

New `AgentExecutionSummary`:

```python
@dataclass
class AgentExecutionSummary:
    comparison_mode: str            # "with_without" | "vs_previous" | "skipped"
    skip_reason: str | None
    runs_per_case: int
    with_skill: ConfigAggregate     # pass_rate/tokens/duration mean+stddev
    baseline: ConfigAggregate
    delta: dict                     # {pass_rate, tokens, duration}
    cases: list[dict]               # per-case: assertion results+evidence, rubric score,
                                    # trajectory summary, permission_violations
```

- `EvaluationReport` gains `agent_execution: AgentExecutionSummary | None`.
- `overall_score` = mean of **available** components: `test_score`, `content_score`, and
  `agent_exec_score = 100 × with_skill pass_rate mean`. Backward-compatible: when
  agent-execution is absent, scoring is unchanged.
- The **delta is reported in `summary`** (and the section), *not* folded into the absolute
  `overall_score` — it is a value-add axis, not an absolute quality score.

## 8. Error handling & degradation

- No model / eval extras missing → `agent_execution.comparison_mode = "skipped"` with a
  reason; deterministic results preserved (existing contract).
- Per-run agent error/timeout → that run recorded as a failed run with detail; the suite
  continues.
- Sandbox create/cleanup always in `try/finally`.
- Permission violation → recorded, case fails, no crash.
- The whole agent-execution pass is wrapped so any unexpected exception degrades to a
  `skipped`/`error` section without losing the rest of the report (mirrors `graph.py`).

## 9. Testing

- **Pure unit (no model):** `assertions.py` over fixture `RunResult`s (every kind, pass +
  fail); `trajectory` parsing; `sandbox` tool-scoping (declared vs denied, violation
  recording, deny-list patterns); new `cases.py` validation rules (including the
  `execute`-missing warning and unknown-`kind` error).
- **Model-dependent:** drive `agent_exec` + `baseline` with a **scripted fake chat model**
  (LangChain `FakeMessagesListChatModel` or equivalent stub) that emits a fixed tool-call
  sequence — fully deterministic, no API calls. Cover: `with_without` delta computation,
  `vs_previous` snapshot path + fallback, multi-run aggregation (mean/stddev), permission
  violation forcing pass_rate 0.
- **Integration:** extend existing CLI tests (`cli/tests`) and API tests
  (`frontend/api/tests/test_evaluation_routes.py`) for `task` cases and the new report
  section; verify sidecar placement still doesn't corrupt the skill ID.
- Lint clean under ruff (line-length 100, E/F/I/UP) per repo config.

## 10. Open considerations (acknowledged, not blocking)

- Pragmatic sandbox is not true isolation; documented and flagged for a future Docker/
  `sandbox-exec` upgrade.
- Persisting agent-execution artifacts (workspaces/transcripts) alongside sidecar reports is
  deferred; v1 deletes them unless `--keep-artifacts`.
- Network is not in the permission action vocabulary (`read/write/create/delete/list/execute`);
  network access during `execute` is governed only by the deny-list in v1.
