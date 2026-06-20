# Agent Skills Framework

Enterprise framework for building, testing, and publishing agent skills for data management and governance.

Full documentation for every part of this repo (architecture, SDKs, CLI,
manifest spec, content-addressing, testing, frontend, security) lives in
[`docs/`](docs/README.md). This file stays a quick human-facing overview;
`docs/` is the single source of truth for detail.

## Project Structure

- `spec/` — Skill manifest JSON Schema and specification docs
- `sdks/python/` — Python SDK (`skill_sdk` package with `BaseSkill`, `SkillContext`, `RegistryClient`, `validate_manifest`, `compute_skill_id`, `FalkorDBConnector`, `SemVer`)
- `sdks/typescript/` — TypeScript SDK (Skill interface + types + `computeSkillId`)
- `cli/` — CLI tool: `skill init`, `validate`, `build`, `publish`, `install`, `list`, `info`, `doc`, `verify`, `sync`, `graph`
- `registry/` — Local filesystem registry with `index.yaml`
- `skills/` — Reference skill implementations (e.g., `data-discovery`)
- `testing/` — Test harness for running skills in isolation
- `frontend/` — React + Vite + Tailwind dashboard + FastAPI backend
  - `frontend/api/` — FastAPI server wrapping Python SDK with REST endpoints
  - `frontend/src/` — React app with Dashboard, Catalog, Skill Detail pages
  - See [`docs/frontend.md`](docs/frontend.md) for full feature/API/architecture docs and [`docs/security.md`](docs/security.md) for the threat model

## Skill Manifest

Every skill has a `SKILL.md` (YAML frontmatter + Markdown body) at its root.
Legacy `skill.yaml` and `skill.json` formats are still accepted but deprecated.

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | kebab-case identifier (2-64 chars) |
| `version` | yes | SemVer (e.g. `1.0.0`) |
| `description` | yes | Human-readable description |
| `runtime` | yes | `python` or `typescript` |
| `api_version` | yes | API contract version |
| `entry` | yes | Entry point relative to skill root |
| `id` | no | SPIFFE-inspired content hash (`skill://sha256/<hash>/<name>@<version>`) |
| `capabilities` | no | Declared capabilities |
| `dependencies` | no | pip/npm/skill dependencies |
| `permissions` | no | Resource access declarations |
| `triggers` | no | Events and commands that invoke the skill |
| `config` | no | Configuration schema and required keys |
| `lifecycle` | no | Install/uninstall/upgrade hook scripts |

## Skill ID (Content-Addressed)

Every published skill gets a **SPIFFE-inspired content hash ID**:

```
skill://sha256/<sha256-of-manifest+source>/<name>@<version>
```

Computed from: canonical manifest JSON (sans `id` field) + all source file contents. Changes to code or manifest produce a different ID, making versions immutable.

## Skill API (Python)

```python
from skill_sdk import BaseSkill, SkillContext, SkillEvent, SkillCommand, SkillResult, HealthStatus

class MySkill(BaseSkill):
    async def initialize(self, ctx: SkillContext) -> None: ...
    async def handle_event(self, event: SkillEvent) -> SkillResult: ...
    async def handle_command(self, command: SkillCommand) -> SkillResult: ...
    async def health_check(self) -> HealthStatus: ...
    async def shutdown(self) -> None: ...
```

## CLI Usage

```bash
skill init my-skill           # Scaffold new skill
skill validate --deep         # Validate (structural + hash + cycle detection)
skill build                   # Build (compute hash, package)
skill publish                 # Publish to registry (stores hash, optional git tag)
skill install my-skill        # Install from registry
skill list                    # List registry (shows hash snippets)
skill info my-skill           # Show skill details
skill doc                     # Generate markdown/json documentation
skill verify my-skill         # Verify integrity (hash matches content)
skill sync --source-url <url> # Sync registry from remote sources
skill graph register          # Register skill in FalkorDB knowledge graph
skill graph query --capability <c>  # Query graph by capability
```

## Testing

Run every suite (Python SDK, CLI, reference skill, harness, TypeScript) with one command:

```bash
make install-ts   # first time only: install TypeScript deps
make test         # or: bash scripts/run_tests.sh
```

Individual suites: `make test-sdk | test-cli | test-skill | test-harness | test-ts`.

Notes:
- `version` accepts full SemVer (`1.2.3`, `1.2.3-rc.1`, `1.0.0+build.5`).
- `publish` is non-destructive — the computed `id` is written into the registry copy, not your source manifest.
- `install` re-verifies content integrity by default; pass `--no-verify` to skip.

## Data Management Domain Skills

- `data-discovery` — Crawl schemas, profile statistics, publish to catalog
- `data-tagging` — Apply business/technical tags to data assets
- `data-quality` — Validate, monitor, and report on quality dimensions
- `data-enrichment` — Augment assets with lineage, glossary, classifications
- `data-lineage` — Track column-level data lineage
- `data-masking` — Apply PII/PHI masking policies

## Knowledge Graph (FalkorDB)

Optional FalkorDB integration for:
- **Capability graph**: which skills provide which capabilities
- **Dependency graph**: skill dependency chains and impact analysis
- **Deployment graph**: where skills are deployed and their status
- **Discovery**: find skills by capability, trace deployment lineage
