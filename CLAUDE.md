# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is the human-facing overview (manifest field table, full CLI command list, domain skill catalog, FalkorDB graph model). [`docs/`](docs/README.md) is the full documentation set for the whole solution (architecture, Python/TypeScript SDK reference, CLI reference, skill manifest spec, content-addressing, testing, frontend, security) — read it for detail. This file covers what you need to *work in* the repo — commands, the cross-file wiring, and the non-obvious gotchas.

## Repo layout (multi-package, no install step)

The repo is a set of loosely-coupled packages that are **not** pip-installed. Code finds the Python SDK via `sys.path`/`PYTHONPATH` manipulation, not an editable install:

- `sdks/python/skill_sdk/` — the authoritative SDK. Everything else imports `skill_sdk`.
- `cli/src/main.py` — the `skill` CLI. At import time it does `sys.path.insert(0, ".../sdks/python")` (main.py:8) so it can import `skill_sdk` without installation.
- `skills/` — reference skills (e.g. `data-discovery`); each is a standalone skill dir with its own `SKILL.md` + `src/` + `tests/`.
- `sdks/typescript/` — a thin mirror of the SDK types; **Python is the source of truth**, keep TS in sync when changing the manifest/ID contract.
- `spec/skill-schema.json` — the published JSON Schema. Note: `validate_manifest` does **not** load it; validation is hand-written validators in `validation.py`. If you change the schema, update both.
- `registry/` — a filesystem registry: `index.yaml` + published skills copied under `registry/skills/<name>-<version>/`.
- `runtime/` — currently empty.

## Commands

Requires Python 3.11+. Only third-party deps are `pyyaml` (+ `pydantic` for the SDK); FalkorDB graph features need `redis`.

```bash
# Run the CLI (no install needed — the script shims sys.path itself)
python cli/src/main.py <command> ...        # e.g. validate, build, publish, list

# Run EVERY suite (Python SDK + CLI + reference skill + harness + TypeScript):
make test                  # or: bash scripts/run_tests.sh
make install-ts            # first-time: install TS deps (cd sdks/typescript && npm install)

# Individual suites (each Python package runs from its own cwd because of import paths):
make test-sdk             # cd sdks/python && python -m pytest
make test-cli             # PYTHONPATH=sdks/python python -m pytest cli/tests  (run from REPO ROOT)
make test-skill           # the data-discovery reference skill
make test-harness         # the testing/ harness
make test-ts              # cd sdks/typescript && npm test (vitest)

# Single test
cd sdks/python && python -m pytest tests/test_hashing.py -q

# Lint (config in sdks/python/pyproject.toml: ruff, line-length 100, rules E/F/I/UP)
make lint                 # cd sdks/python && ruff check .

# Cross-check every published skill's id against its recorded git tag
make verify-published      # PYTHONPATH=sdks/python python cli/src/main.py verify-git --all --registry registry
```

`.github/workflows/ci.yml` runs `make test` then `make verify-published` on push/PR. The
`verify-published` step is `continue-on-error: true` — it can correctly flag historical
git/registry drift (a tag created before the tagged skill's source was committed) that's
unrelated to the PR under review; treat a red check there as informational, not a gate.

`scripts/run_tests.sh` / the `Makefile` are the aggregate runner: each Python package is
imported from a different root, so the runner enters each package's dir with `PYTHONPATH`
pointed at `sdks/python`. pytest-asyncio is a declared test extra (`pip install -e
sdks/python[test]`); `asyncio_mode = auto` is set in each package's pytest config.

## Content-addressed skill IDs (the core invariant)

Every skill has a SPIFFE-inspired immutable ID: `skill://sha256/<digest>/<name>@<version>`.

- `compute_skill_id` (`hashing.py`) hashes the **canonical manifest JSON with the `id` field stripped** (`sort_keys=True`, compact separators, `ensure_ascii=False`), then appends every source file as `posix_relpath \x00 bytes \x00`, sorted by POSIX path. The file set is defined by `iter_source_files`: **all files of any extension/binary** EXCEPT the manifests, dotfiles/dotdirs, `__pycache__`/`node_modules`/`dist`, and **tests** (`tests/` dirs and `test_*.py`/`*_test.py`/`conftest.py`/`*.test.ts` files). So editing a test does NOT change the ID, but a shipped `.sh`/asset does. POSIX paths + `ensure_ascii=False` make the digest **identical across OSes** and **byte-compatible with the TypeScript SDK**.
- **`publish()` is non-destructive**: it computes the ID and writes it only into the registry's *copy* of the manifest. Your source `SKILL.md`/`skill.yaml`/`skill.json` is never modified. (`cmd_build` writes the stamped manifest into `dist/` only.)
- Published `version` is **full SemVer** — `1.0.0`, `1.2.3-rc.1`, `1.0.0+build.5` all validate; the same grammar is reused by dir-name parsing (`<name>-<version>`), git tags, and the JSON schema (`spec/versioning.py:SEMVER_PATTERN` is the single source of truth).
- `validate --deep` recomputes the hash and fails on mismatch (`validate_skill_id`), and runs **transitive** dependency-cycle detection (resolving peers through the registry — see below).
- `install` re-verifies integrity by default (recomputes the ID against the registry's recorded one); `--no-verify` skips it.

## How the pieces flow

- **Validation** (`validation.py`): `validate_full_skill` → `validate_manifest_file` → `validate_manifest` (per-field `_validate_*` helpers) → optional ID + cycle checks. All structural rules (kebab-case names, SemVer via `versioning.is_semver`, runtime ∈ {python,typescript}, command must start with `/`, skill deps must be `name@range`, permission actions whitelist) live here, not in the JSON schema. A missing `tests/` dir is a **non-fatal** `lint_full_skill` warning, not a hard error (it used to block `build`). `detect_dependency_cycles(manifest, registry)` walks the graph transitively via `registry.get_skill_dependencies(name)`; without a registry it only catches self-loops.
- **Registry** (`registry.py` `RegistryClient`): filesystem-backed. All index mutations (`publish`/`add_source`/`sync_from_sources`) run under an **exclusive file lock** (`_locked`, `fcntl`) and `_save_index` writes atomically (temp + `os.replace`) — safe under concurrent writers. `publish` copies the tree (`COPY_IGNORE` drops dotfiles incl. `.env`, caches, `dist`), stamps the id into the copy, updates `index.yaml` (`skills.<name>` → `versions`/`latest`/`ids`/`locations`/`git_tags`), and records the git tag it created. `latest` is the **SemVer max**, not most-recently-published. `install`/`verify` as above; `sync_from_sources` returns `{synced, skills, errors}`. After the lock is released, `publish` also best-effort syncs to FalkorDB via `self.graph` (a `RegistryClient(..., graph=FalkorDBConnector(...))` constructor arg, wired up from `SKILLS_GRAPH_HOST`/`SKILLS_GRAPH_PORT` in both `cli/src/main.py` and `frontend/api/deps.py`) — graph sync deliberately happens *outside* `_locked()` since network I/O must never hold the index file lock; a connect/register failure is swallowed and reported back as `result["graph"]`, never raised.
- **Graph** (`graph.py` `FalkorDBConnector`): optional Cypher-over-redis integration; **degrades gracefully** — missing `redis` or a failed connect returns `False`/empty rather than raising, so graph features are always opt-in via `--graph-host`/`SKILLS_GRAPH_HOST`. `register_skill` also links each manifest's `permissions` as `Permission` nodes via `REQUESTS` edges, queryable with `find_skills_by_permission`. `find_impact` walks `DEPENDS_ON*` **forward** (what a skill depends on) — for the inverse ("what depends on this skill"), use the registry-only `validation.find_downstream_skills()` instead; the two are intentionally separate, not a refactor of one into the other.
- **Git drift verification** (`git_verify.py` `verify_against_git`): distinct from `RegistryClient.verify()` (which only checks the registry's stored copy against its own recorded id). Checks out the skill's recorded `skill/<name>/<version>` git tag into a disposable `git worktree`, locates the matching manifest by searching the tree for `name`+`version` (not a stored path — works for tags predating this feature), and recomputes/compares the id. Backs `skill verify-git` and `make verify-published`.
- **Skill runtime contract** (`base.py` + `context.py`): a skill subclasses `BaseSkill` and implements the async lifecycle `initialize / handle_event / handle_command / health_check / shutdown`. The CLI `init` scaffolds exactly this shape. `testing/harness.py` (`SkillTestHarness`) can `load_skill()` (import the entry point, find the `BaseSkill` subclass) and drive it with `initialize`/`run_command`/`run_event`/`health`.
- **TypeScript parity** (`sdks/typescript/src/index.ts`): `computeSkillId` is async and **byte-compatible** with Python — `canonicalJson` recursively sorts keys with compact separators, the `id` field is stripped, files use the same `path \x00 content \x00` framing. The cross-language golden lives in `sdks/typescript/test/parity.fixture.json` (regenerate from Python if the hash algorithm changes). Caller supplies `sourceFiles` as posix-relative → UTF-8 text (no binary).

## Conventions

- The manifest is `SKILL.md` (YAML frontmatter between `---` delimiters + a Markdown body of agent-facing instructions) — the Anthropic-standard skill format and now the preferred one. Legacy pure `skill.yaml`/`skill.yml`/`skill.json` files are still read for backward compatibility but are deprecated. Every code path that locates a manifest (`find_manifest_file` in `validation.py`, and the duplicated `_manifest_path` probes in `registry.py` and `frontend/api/routes/skills.py`) probes in the fixed order `SKILL.md` → `skill.yaml` → `skill.yml` → `skill.json`; preserve that ordering when adding new manifest handling. `_parse_frontmatter()` does the frontmatter split/parse and is reused by every writer (`registry.py`'s `_write_skill_md`, `cli/src/main.py`'s `cmd_build`) to splice an updated frontmatter block back in while preserving the existing Markdown body verbatim.
- The Python and TypeScript ID/manifest contracts must stay byte-compatible — `computeSkillId` in TS mirrors `compute_skill_id` in Python.
