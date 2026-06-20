# Architecture

## Big picture

The repo is a set of loosely-coupled packages, not a single installed
application. Nothing is `pip install`-ed or `npm link`-ed across package
boundaries — each consumer wires up the producer's source directly:

- The **CLI** (`cli/src/main.py`) inserts `sdks/python` onto `sys.path` at
  import time and imports `skill_sdk` directly.
- The **frontend backend** (`frontend/api/main.py`) does the exact same
  `sys.path` insert, so it calls the *same* `skill_sdk` functions the CLI
  does — there is no parallel reimplementation of registry/validation/hashing
  logic in the API layer.
- The **test harness** (`testing/harness.py`) imports `skill_sdk` normally
  (it runs with `PYTHONPATH` pointed at `sdks/python`) and additionally
  dynamically imports a *skill's* entry point at runtime via
  `importlib.util`, to drive its lifecycle without that skill being
  installed anywhere.
- The **TypeScript SDK** (`sdks/typescript/`) is an independent package with
  its own `computeSkillId`, deliberately kept byte-compatible with the
  Python implementation (same canonical JSON, same hashing algorithm) so a
  skill ID computed by either language is identical. Python is the source of
  truth; TypeScript mirrors it.

```
                    ┌─────────────────────┐
                    │   sdks/python/       │   <- single source of truth for
                    │   skill_sdk package  │      manifest validation, hashing,
                    └──────────┬───────────┘      versioning, registry ops
                               │  sys.path insert
            ┌──────────────────┼───────────────────┐
            │                  │                   │
   ┌────────▼────────┐ ┌───────▼────────┐  ┌───────▼─────────┐
   │ cli/src/main.py  │ │ frontend/api/  │  │ testing/         │
   │ `skill` CLI      │ │ FastAPI server │  │ SkillTestHarness │
   └────────┬─────────┘ └───────┬────────┘  └──────────────────┘
            │                   │
            └─────────┬─────────┘
                       │ both read/write
                       ▼
              ┌──────────────────┐
              │   registry/       │   filesystem registry: index.yaml +
              │   index.yaml      │   registry/skills/<name>-<version>/
              └──────────────────┘
```

The **dashboard frontend** (`frontend/src/`, a separate React/Vite app) talks
to the FastAPI backend over HTTP (`/api/*`) — it never touches the filesystem
or `skill_sdk` directly. See [frontend.md](./frontend.md) for that layer's
own internal architecture.

## The core invariant: content-addressed skill IDs

Every published skill gets an immutable, SPIFFE-inspired ID:

```
skill://sha256/<digest>/<name>@<version>
```

The digest is computed from the canonical manifest (with `id` stripped) plus
every source file's contents — so the ID changes if *either* the manifest or
any shipped file changes, and is identical regardless of OS or which SDK
(Python or TypeScript) computed it. This one property is what makes
`verify`/`install --verify` meaningful, and it's why `publish` never mutates
your source tree (the ID is written only into the registry's copy). Full
details: [content-addressing.md](./content-addressing.md).

## How a skill moves through the system

1. **Author** — `skill init <name>` scaffolds a `SKILL.md` + `src/main.py` +
   `tests/` from a template (`cli/src/main.py:cmd_init`).
2. **Validate** — `skill validate --deep` runs structural checks
   (`validation.py`), then optionally hash verification and dependency-cycle
   detection.
3. **Build** — `skill build` computes the skill ID and writes a stamped copy
   into `dist/`, without touching the source manifest.
4. **Publish** — `skill publish` (or the dashboard's scaffold-and-publish
   flow) copies the skill tree into `registry/skills/<name>-<version>/`,
   stamps the ID into *that copy only*, updates `registry/index.yaml` under
   an exclusive file lock, and optionally creates a git tag
   (`skill/<name>/<version>`).
5. **Discover** — `skill list` / `GET /api/skills` reads the index; `skill
   info` / the Skill Detail page reads a single entry plus the published
   manifest.
6. **Install** — `skill install <name>` (or `POST /api/skills/{name}/install`)
   copies the published skill tree to a target directory and, by default,
   recomputes the hash to detect tampering before keeping it.
7. **Run** — a host process implements the lifecycle contract
   (`BaseSkill`/`Skill` in TS) and drives `initialize` → `handle_event` /
   `handle_command` → `health_check` → `shutdown`. The test harness exercises
   exactly this contract in isolation for automated tests.
8. **Sync** (optional) — `skill sync` / `POST /api/registry/sync` pulls
   additional versions from configured `local` or `git` sources into the same
   index.
9. **Graph** (optional) — `skill graph register` / the Knowledge Graph page
   can mirror a skill's capabilities/dependencies into FalkorDB for capability
   search and impact analysis. This is fully optional — missing `redis` or a
   failed connection degrades to "not connected" rather than raising.

## Why three different runners read the registry the same way

Both the CLI and the FastAPI backend construct a `RegistryClient` pointed at
the same `registry/` directory and call the same methods
(`list_skills`, `info`, `publish`, `install`, `verify`, `sync_from_sources`).
This is intentional: the dashboard is explicitly *not* a separate system with
its own notion of what's published — it's a UI over the identical registry the
CLI manages, so `skill publish` from a terminal and "Publish" from the
dashboard produce indistinguishable registry state.

## Concurrency and durability

`RegistryClient` treats the registry as shared, possibly-concurrent state:

- `index.yaml` reads/writes are wrapped in an exclusive `fcntl` lock
  (`_locked()`), and writes are atomic (`tempfile.mkstemp` + `fsync` +
  `os.replace`) so a crash mid-write can never leave a corrupt or
  half-written index.
- The dashboard's audit log (`registry/.audit.jsonl`) is append-only with the
  same `fcntl` locking discipline, so concurrent writers can't interleave
  partial lines.

## Where validation rules actually live

The published JSON Schema (`spec/skill-schema.json`) documents the manifest
shape, but **it is not what enforces it**. All real structural validation —
kebab-case names, full-SemVer versions, runtime enum, permission action
whitelist, skill-dependency `name@range` syntax — lives in hand-written
validators in `sdks/python/skill_sdk/validation.py`. If you change a
validation rule, update both files; they're meant to agree but aren't
mechanically linked.
