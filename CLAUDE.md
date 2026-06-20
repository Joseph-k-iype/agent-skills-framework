# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is the human-facing overview (manifest field table, full CLI command list, domain skill catalog, FalkorDB graph model). Read it for reference; this file covers what you need to *work in* the repo — commands, the cross-file wiring, and the non-obvious gotchas.

## Repo layout (multi-package, no install step)

The repo is a set of loosely-coupled packages that are **not** pip-installed. Code finds the Python SDK via `sys.path`/`PYTHONPATH` manipulation, not an editable install:

- `sdks/python/skill_sdk/` — the authoritative SDK. Everything else imports `skill_sdk`.
- `cli/src/main.py` — the `skill` CLI. At import time it does `sys.path.insert(0, ".../sdks/python")` (main.py:8) so it can import `skill_sdk` without installation.
- `skills/` — reference skills (e.g. `data-discovery`); each is a standalone skill dir with its own `skill.yaml` + `src/` + `tests/`.
- `sdks/typescript/` — a thin mirror of the SDK types; **Python is the source of truth**, keep TS in sync when changing the manifest/ID contract.
- `spec/skill-schema.json` — the published JSON Schema. Note: `validate_manifest` does **not** load it; validation is hand-written validators in `validation.py`. If you change the schema, update both.
- `registry/` — a filesystem registry: `index.yaml` + published skills copied under `registry/skills/<name>-<version>/`.
- `runtime/` — currently empty.

## Commands

Requires Python 3.11+. Only third-party deps are `pyyaml` (+ `pydantic` for the SDK); FalkorDB graph features need `redis`.

```bash
# Run the CLI (no install needed — the script shims sys.path itself)
python cli/src/main.py <command> ...        # e.g. validate, build, publish, list

# Tests — each package runs from its own cwd because of the import paths:
cd sdks/python && python -m pytest                      # SDK suite (pyproject sets testpaths=tests)
python -m pytest cli/tests                              # CLI suite — run from REPO ROOT (imports `cli.src.main`)
cd skills/data-discovery && PYTHONPATH=../../sdks/python python -m pytest   # a skill's own tests

# Single test
cd sdks/python && python -m pytest tests/test_hashing.py::TestComputeSkillId -q

# Lint (config in sdks/python/pyproject.toml: ruff, line-length 100, rules E/F/I/UP)
cd sdks/python && ruff check .
```

There is no repo-root pytest config or aggregate test runner; run each package's suite separately as above.

## Content-addressed skill IDs (the core invariant)

Every skill has a SPIFFE-inspired immutable ID: `skill://sha256/<digest>/<name>@<version>`.

- `compute_skill_id` (`hashing.py`) hashes the **canonical manifest JSON with the `id` field stripped**, then appends every source file's relative path + bytes, sorted. It deliberately excludes the manifest files themselves, dotfiles, `__pycache__`, `node_modules`, and `dist` — so adding the `id` back into the manifest doesn't change the hash. Any change to code or manifest fields → different ID → a new immutable version.
- **`publish()` mutates the source manifest in place**: it computes the ID and writes it back into your `skill.yaml`/`skill.json` *before* copying to the registry (`registry.py` `publish`). Expect your working-tree manifest to gain an `id:` field after publish/build.
- `validate --deep` recomputes the hash and fails on mismatch (`validate_skill_id`), plus runs dependency-cycle detection.

## How the pieces flow

- **Validation** (`validation.py`): `validate_full_skill` → `validate_manifest_file` → `validate_manifest` (per-field `_validate_*` helpers) → optional ID + cycle checks. All structural rules (kebab-case names, SemVer, runtime ∈ {python,typescript}, command must start with `/`, skill deps must be `name@range`, permission actions whitelist) live here, not in the JSON schema.
- **Registry** (`registry.py` `RegistryClient`): filesystem-backed. `publish` validates → copies tree → updates `index.yaml` (`skills.<name>` with `versions`/`latest`/`ids`/`locations`) → optionally creates a git tag `skill/<name>/<version>` (`versioning.py`, auto on if a `.git` ancestor exists). `install` copies from the registry into a target dir; `verify` re-validates stored files; `sync_from_sources` pulls from configured `sources` (local/git, `sources.py`).
- **Graph** (`graph.py` `FalkorDBConnector`): optional Cypher-over-redis integration; **degrades gracefully** — missing `redis` or a failed connect returns `False`/empty rather than raising, so graph features are always opt-in via `--graph-host`.
- **Skill runtime contract** (`base.py` + `context.py`): a skill subclasses `BaseSkill` and implements the async lifecycle `initialize / handle_event / handle_command / health_check / shutdown`. The CLI `init` scaffolds exactly this shape. `testing/harness.py` (`SkillTestHarness`) builds a `SkillContext`/events/commands from a manifest for unit tests.

## Conventions

- Manifests may be `skill.yaml` **or** `skill.json`; nearly every code path probes `skill.yaml` first, then falls back to `.json`. Preserve that ordering when adding new manifest handling.
- The Python and TypeScript ID/manifest contracts must stay byte-compatible — `computeSkillId` in TS mirrors `compute_skill_id` in Python.
