# Documentation

This is the single home for documentation across the whole Agent Skills
Framework — the SDKs, CLI, registry, reference skills, test harness, and the
web dashboard. If you're looking for how something works or how to run it,
start here.

| Doc | Covers |
|---|---|
| [architecture.md](./architecture.md) | How the packages fit together, the repo layout, and the request/data flow end to end |
| [getting-started.md](./getting-started.md) | Install/run instructions for every package — CLI, SDKs, tests, dashboard |
| [skill-manifest.md](./skill-manifest.md) | The `SKILL.md`/`skill.yaml`/`skill.json` schema, field-by-field, with a full example |
| [content-addressing.md](./content-addressing.md) | How skill IDs are computed, why publish is non-destructive, SemVer rules |
| [python-sdk.md](./python-sdk.md) | `skill_sdk` package reference: `BaseSkill`, `RegistryClient`, validation, hashing, versioning, sources, graph |
| [typescript-sdk.md](./typescript-sdk.md) | TypeScript SDK reference and its parity contract with the Python SDK |
| [cli.md](./cli.md) | Every `skill` CLI subcommand and flag |
| [testing.md](./testing.md) | The test harness API, aggregate test runner, and per-package test commands |
| [frontend.md](./frontend.md) | The dashboard: tech stack, architecture, every page/feature, full REST API surface |
| [security.md](./security.md) | Threat model for the dashboard: path sandboxing, API-key auth, the known per-user-authz gap |

## Repo map

```
spec/             Skill manifest JSON Schema + spec docs
sdks/python/      Python SDK (skill_sdk) — source of truth for the ID/manifest contract
sdks/typescript/  TypeScript SDK — byte-compatible mirror of the Python hashing contract
cli/              `skill` CLI (init, validate, build, publish, install, list, info, doc, verify, verify-git, sync, graph)
registry/         Filesystem skill registry (index.yaml + copied, content-addressed skill trees)
skills/           Reference skill implementations (e.g. data-discovery)
testing/          Test harness for running a skill's lifecycle in isolation
frontend/         FastAPI + React dashboard over the same registry
scripts/          Aggregate test runner
```

`AGENTS.md` (repo root) is the short human-facing project overview; `CLAUDE.md`
(repo root) is the Claude Code working-agreement for this repo. Both link here
for depth instead of duplicating it.
