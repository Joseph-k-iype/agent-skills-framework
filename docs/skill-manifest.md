# Skill manifest reference

Every skill has a manifest at its root: `SKILL.md` (YAML frontmatter + Markdown
body — preferred). Legacy `skill.yaml`, `skill.yml`, and `skill.json` are still
supported but deprecated. Code paths that look for a manifest probe
`SKILL.md` first, then fall back to `skill.yaml` / `skill.yml` / `skill.json`.

The frontmatter contains all structured manifest fields; the Markdown body
provides agent-facing instructions (used by AI agents that consume the skill).

The published JSON Schema lives at `spec/skill-schema.json`, but the rules
that actually run live in hand-written validators in
`sdks/python/skill_sdk/validation.py` (`_validate_*` functions) — that file is
the source of truth; keep the schema in sync with it, not the other way
around.

## Fields

| Field | Required | Type | Rules |
|---|---|---|---|
| `name` | yes | string | kebab-case (`^[a-z][a-z0-9-]*$`), 2–64 chars |
| `version` | yes | string | full SemVer — `1.0.0`, `1.2.3-rc.1`, `1.0.0+build.5` |
| `runtime` | yes | string | `python` or `typescript` |
| `api_version` | yes | int | `>= 1` |
| `entry` | yes | string | path relative to skill root; `.py` for python runtime, `.ts`/`.js` for typescript runtime; must exist on disk when validated with a skill root |
| `id` | no | string | content-addressed ID, see [content-addressing.md](./content-addressing.md). Never set this by hand — it's computed and stamped by `build`/`publish` |
| `description` | yes | string | free text — required for agent interoperability (agentskills.io standard) |
| `capabilities` | no | string[] | non-empty strings; used for capability-based discovery and the knowledge graph |
| `triggers.events` | no | string[] | non-empty strings |
| `triggers.commands` | no | string[] | each must start with `/` |
| `config.required` | no | string[] | required config keys |
| `config.schema` | no | object | arbitrary config schema |
| `dependencies.pip` | no | string[] | pip requirement strings |
| `dependencies.npm` | no | string[] | npm package strings |
| `dependencies.skills` | no | string[] | `name@range`, e.g. `data-quality@^1.0.0` — `@` is required, the name part must be kebab-case |
| `permissions` | no | array | each entry: `{resource: string, actions: string[]}` |
| `permissions[].actions` | — | string[] | each action must be one of `read`, `write`, `create`, `delete`, `list`, `execute` |
| `lifecycle.on_install` / `on_uninstall` / `on_upgrade` | no | string | hook script paths; no other keys are allowed under `lifecycle` |

## Full example

```yaml
---
name: data-discovery
version: 0.1.0
description: Discovers and catalogs data assets across configured sources.
runtime: python
api_version: 1
entry: src/main.py
capabilities:
  - schema-discovery
  - statistics-profiling
triggers:
  events:
    - source.connected
  commands:
    - /discover
config:
  required:
    - connection_string
  schema:
    connection_string: { type: string }
dependencies:
  pip:
    - sqlalchemy>=2.0
  skills:
    - data-tagging@^1.0.0
permissions:
  - resource: database:metadata
    actions: [read, list]
lifecycle:
  on_install: scripts/setup.sh
---

# Data Discovery

Agent instructions for discovering and cataloging data assets.
```

## Directory layout

```
my-skill/
├── SKILL.md            # manifest frontmatter + agent instructions (required)
├── src/
│   └── main.py          # entry point — matches the `entry` field
├── tests/                # excluded from the skill ID hash (see content-addressing.md)
├── scripts/              # optional lifecycle hook scripts
└── README.md             # optional
```

## Runtime contract

A skill subclasses `BaseSkill` (Python) or implements `Skill` (TypeScript) and
exposes the same five-method async lifecycle in both languages. See
[python-sdk.md](./python-sdk.md#baseskill-lifecycle) and
[typescript-sdk.md](./typescript-sdk.md) for the exact interfaces.

## Linting vs. hard validation

`lint_full_skill()` produces **non-fatal warnings** — currently just "missing
`tests/` directory" — that show up in CLI output and the dashboard's Validate
tab but never block `build`/`publish`. Everything in `validate_full_skill()`
is a hard error that blocks both.
