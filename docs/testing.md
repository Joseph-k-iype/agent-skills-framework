# Testing

This repo has five independent test suites, each importing `skill_sdk` from a
different working directory (no editable install — every package shims its
own `PYTHONPATH`). `make test` / `scripts/run_tests.sh` is the aggregate
runner that knows how to invoke each one correctly.

## Run everything

```bash
make install-ts   # first time only: cd sdks/typescript && npm install
make test         # == bash scripts/run_tests.sh
```

`run_tests.sh` runs each suite from its correct `cwd` with `PYTHONPATH`
pointed at `sdks/python`, auto-detects `python3` vs `python`, skips the
TypeScript suite gracefully if `node_modules` isn't installed yet, and
exits non-zero (printing a PASS/FAIL summary) if any suite fails.

## Run one suite at a time

| Target | Equivalent command | What it covers |
|---|---|---|
| `make test-sdk` | `cd sdks/python && python3 -m pytest -q` | `skill_sdk` unit tests: hashing, versioning, validation, registry, sources |
| `make test-cli` | `PYTHONPATH=sdks/python python3 -m pytest cli/tests -q` (from repo root) | the `skill` CLI's commands end-to-end |
| `make test-skill` | `cd skills/data-discovery && PYTHONPATH=<repo>/sdks/python python3 -m pytest -q` | the reference skill's own tests |
| `make test-harness` | `cd testing && PYTHONPATH=<repo>/sdks/python python3 -m pytest -q` | `SkillTestHarness` itself, using `data-discovery` as a live fixture |
| `make test-ts` | `cd sdks/typescript && npm test` (vitest) | TypeScript SDK, including the cross-language hashing parity fixture |
| `make test-py` | runs sdk + cli + skill + harness | every Python suite, skipping TS |

A single test file:

```bash
cd sdks/python && python -m pytest tests/test_hashing.py -q
```

`pytest-asyncio` is a declared extra
(`pip install -e sdks/python[test]`) and `asyncio_mode = "auto"` is set in
every package's pytest config, so `async def test_...` functions just work
without `@pytest.mark.asyncio`.

## Frontend tests (separate from the suites above)

The dashboard has its own backend/frontend test commands, documented in
[frontend.md](./frontend.md#tests) — they're not part of `make test` because
the dashboard is an optional layer with its own dependency set
(`fastapi`, `httpx`, npm/vitest).

## The test harness (`testing/harness.py`)

`SkillTestHarness` lets you drive a skill's real lifecycle in isolation
without installing or deploying it:

```python
from testing.harness import SkillTestHarness

harness = SkillTestHarness("skills/data-discovery")
ctx = await harness.initialize({"connection_string": "..."})  # config overrides
result = await harness.run_command("discover", args=["--source", "warehouse"])
result = await harness.run_event("source.connected", {"id": "abc"})
health = await harness.health()
await harness.shutdown()
```

Under the hood: `load_skill()` reads the manifest's `entry` field, imports
that file via `importlib.util` (so the skill doesn't need to be on
`sys.path` or installed anywhere), finds the `BaseSkill` subclass defined in
it, and instantiates it. `create_context()`/`make_event()`/`make_command()`
build the dataclasses from `skill_sdk.context` directly if you want to drive
the skill manually instead of using the convenience methods above.

## Writing tests for a new skill

A skill's own `tests/` directory is excluded from its content-hash (see
[content-addressing.md](./content-addressing.md)) — editing tests never
changes the skill's published ID. Reference `skills/data-discovery/tests/`
and `skills/data-discovery/pytest.ini` for the expected layout
(`testpaths = tests`, `asyncio_mode = auto`).

## Agent-execution eval (task cases)

A `task` case runs a real LLM agent that follows the skill's SKILL.md in a
temporary, permission-scoped workspace, then grades the workspace + trajectory
against a baseline (with/without skill, or vs the previous published version).

> **Safety:** the shell sandbox is *pragmatic*, not true isolation — commands run
> with the working directory locked to a temp workspace, a minimized environment,
> a timeout, and a destructive-pattern deny-list. A determined command could still
> affect the host. Only run agent-execution evals on skills you trust, or in a
> disposable/CI environment. Container-level isolation is a planned upgrade.
