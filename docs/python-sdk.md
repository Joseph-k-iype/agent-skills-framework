# Python SDK reference (`skill_sdk`)

Location: `sdks/python/skill_sdk/`. This package is the source of truth for
the manifest/ID contract — the CLI, the dashboard backend, and the test
harness all import it directly via a `sys.path` insert rather than an
installed dependency. Third-party deps: `pyyaml`, `pydantic`; `redis` is only
needed for the optional FalkorDB graph features.

```python
from skill_sdk import (
    BaseSkill, SkillContext, SkillEvent, SkillCommand, SkillResult, HealthStatus,
    RegistryClient,
    validate_manifest, ValidationError,
    compute_skill_id, validate_skill_id, hash_from_skill_id,
    SemVer, satisfies, resolve_latest, git_tag_skill,
    FalkorDBConnector,
    LocalSource, GitSource, create_source,
    generate_skill_doc,
)
```

## `BaseSkill` lifecycle (`base.py`, `context.py`)

A skill subclasses `BaseSkill` and implements five async methods:

```python
class BaseSkill(ABC):
    name: str
    version: str
    skill_id: str = ""

    async def initialize(self, ctx: SkillContext) -> None: ...
    async def handle_event(self, event: SkillEvent) -> SkillResult: ...
    async def handle_command(self, command: SkillCommand) -> SkillResult: ...
    async def health_check(self) -> HealthStatus: ...
    async def shutdown(self) -> None: ...
```

Supporting dataclasses (`context.py`):

| Type | Fields |
|---|---|
| `SkillContext` | `config: dict`, `logger`, `registry`, `state: dict`, `graph` |
| `SkillEvent` | `name: str`, `payload: dict`, `source: str` |
| `SkillCommand` | `name: str`, `args: list[str]`, `kwargs: dict[str, str]` |
| `SkillResult` | `status: str`, `data: dict`, `error: str \| None`, `message: str` |
| `HealthStatus` | `healthy: bool`, `version: str`, `details: dict` |

This is the exact shape `testing.harness.SkillTestHarness` drives — see
[testing.md](./testing.md).

## `validation.py`

- `load_manifest(path)` — reads `SKILL.md`/`skill.yaml`/`.yml`/`.json`, raises
  `ValidationError` on malformed YAML/JSON.
- `validate_manifest(manifest) -> list[str]` — runs every `_validate_*`
  field check (required fields, name, version via `versioning.is_semver`,
  runtime, api_version, entry, triggers, capabilities, config, dependencies,
  skill-dependency `name@range` syntax, permissions action whitelist,
  lifecycle hooks). Full field rules: [skill-manifest.md](./skill-manifest.md).
- `validate_manifest_with_path(manifest, skill_root)` — same, plus checks the
  `entry` file actually exists under `skill_root`.
- `validate_full_skill(skill_dir) -> list[str]` — loads the manifest from a
  directory and runs the above; this is what gates `build`/`publish`.
- `lint_full_skill(skill_dir) -> list[str]` — **non-fatal** warnings (today:
  missing `tests/` dir). Surfaced in CLI/dashboard output but never blocks
  anything.
- `detect_dependency_cycles(manifest, registry_client=None)` — DFS over
  declared `dependencies.skills`, resolving transitively through
  `registry_client.get_skill_dependencies(name)` when a registry is passed
  (so it can catch cycles across already-published skills, not just within
  one manifest's own declared deps). Without a registry it only catches
  self-loops.
- `ValidationError(message, errors=[...])` — raised throughout the SDK;
  `str(e)` renders the message plus a bulleted list of `errors`.

## `hashing.py`

See [content-addressing.md](./content-addressing.md) for the full algorithm.
Public functions: `compute_skill_id`, `validate_skill_id`,
`hash_from_skill_id`, `name_version_from_skill_id`, `iter_source_files`.

## `versioning.py`

- `SemVer` — parses/compares full SemVer including prerelease + build
  metadata, with spec-correct precedence (`__lt__`, `__eq__`, `__hash__`).
- `is_semver(s) -> bool`.
- `satisfies(version, range_str) -> bool` — `^`, `~`, comparator
  (`>=`, `<`, etc.), and partial (`1.2`, `1.x`) ranges, npm semantics
  including the 0.x caret special case.
- `max_version(versions: list[str]) -> str | None` — SemVer-correct max,
  ignoring unparseable entries; this is what "latest" means everywhere in the
  registry.
- `resolve_latest(versions, range_str=None) -> str | None` — max version that
  satisfies an optional range.
- `git_tag_skill(name, version, skill_id, repo_root)` — creates an annotated
  tag `skill/<name>/<version>`.
- `git_tag_exists(name, version, repo_root) -> bool` — **exact** match
  against `git tag --list` output.

## `registry.py` — `RegistryClient`

Filesystem-backed registry over `<registry_path>/index.yaml` +
`<registry_path>/skills/<name>-<version>/`.

```python
registry = RegistryClient(registry_path, auto_tag=True)

registry.publish(skill_path, force=False, tag=None) -> dict   # {name, version, id, path, git_tag}
registry.list_skills() -> dict                                  # {name: {latest, versions, ids}}
registry.info(name) -> dict                                     # full index entry incl. locations
registry.install(name, target_dir=None, version=None, source=None, verify=True) -> Path
registry.verify(name, version=None) -> dict                      # {valid, errors} or {valid, name, version, id}
registry.add_source(source_config: dict) -> dict
registry.sync_from_sources() -> dict                             # {synced, skills, errors}
registry.get_skill_dependencies(name) -> list[str]               # used by cycle detection
```

Notes:

- **Concurrency-safe**: every index read-modify-write is wrapped in an
  exclusive `fcntl` lock (`_locked()`) and saved atomically (temp file +
  `fsync` + `os.replace`), so concurrent `publish`/`sync` calls can't corrupt
  or lose updates to `index.yaml`.
- **Non-destructive publish**: see [content-addressing.md](./content-addressing.md#non-destructive-publish).
  `COPY_IGNORE` drops `.git`, `__pycache__`, `node_modules`, `dist`, all
  dotfiles, and `*.egg-info` when copying into the registry.
- **`install(..., verify=True)`** recomputes the skill ID after copying and
  raises (cleaning up the partial copy) if it doesn't match the registry's
  recorded ID — this is what catches tampering or corruption between publish
  and install.
- `auto_tag` controls whether `publish()` creates a git tag by default; the
  dashboard's shared client explicitly sets this `False` so browsing the API
  never has the side effect of tagging the repo.

## `sources.py`

`LocalSource` and `GitSource` both implement `list_skills()` (scanning a
directory of `<name>-<version>` dirs, or a git ref, for manifests) and
`fetch(name, version, target_dir)`. `create_source(config: dict)` builds the
right one from `{"type": "local", "path": ...}` or `{"type": "git", "url":
..., "ref": ..., "cache": ...}`, raising a clear `ValueError` if required keys
are missing. `GitSource._ensure_clone()` runs `git fetch --tags --force` on a
cached clone so version discovery doesn't go stale. Both sources select
"latest" via `versioning.max_version()`.

## `adapter.py`

`generate_skill_doc(manifest_path, format="markdown"|"json", output_path=None)`
renders a skill's manifest into human-readable docs — markdown for display, or
a JSON doc object (`{description, entry, lifecycle, ...}` plus the rest of the
manifest fields) for programmatic consumption. Used by `skill doc` and
`GET /api/skills/{name}/doc`.

## `graph.py` — `FalkorDBConnector`

Optional Cypher-over-Redis integration; **always degrades gracefully** —
missing the `redis` package or a failed connection makes `connect()` return
`False` rather than raising, so every graph feature is opt-in.

```python
graph = FalkorDBConnector(host="localhost", port=6379, graph_name="agent-skills")
await graph.connect() -> bool
graph.register_skill(manifest_path) -> dict       # creates Skill/SkillVersion nodes, PROVIDES/DEPENDS_ON edges
graph.find_skills_by_capability(capability) -> list[dict]
graph.find_impact(skill_id) -> list[dict]          # walks DEPENDS_ON* to find what depends on a skill
graph.register_deployment(skill_id, deployment_id, platform, environment, status="active") -> dict
graph.disconnect()
```

The graph model: `Skill` —`VERSION_OF`→ `SkillVersion` —`PROVIDES`→
`Capability`; `SkillVersion` —`DEPENDS_ON`→ `Skill`; `SkillVersion`
—`DEPLOYED_AT`→ `Deployment`.
