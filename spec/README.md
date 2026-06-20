# Agent Skill Specification

This directory defines the canonical specification for enterprise agent skills.

## Schema

- `skill-schema.json` — JSON Schema for validating skill manifests

## Skill Manifest (`skill.yaml`)

Every skill MUST include a `skill.yaml` manifest in its root directory.
The manifest declares:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Unique identifier (kebab-case) |
| `version` | yes | SemVer version |
| `runtime` | yes | `python` or `typescript` |
| `api_version` | yes | API contract version (currently `1`) |
| `entry` | yes | Path to entry point relative to skill root |
| `description` | no | Human-readable description |
| `triggers` | no | Events and commands that invoke the skill |
| `capabilities` | no | Declared capabilities for dependency resolution |
| `config` | no | Configuration schema and required keys |
| `dependencies` | no | Runtime and inter-skill dependencies |
| `permissions` | no | Declared resource access requirements |
| `lifecycle` | no | Install/uninstall/upgrade hook scripts |

## Skill API

Every skill MUST export a handler matching the API contract.

### Python

```python
from skill_sdk import BaseSkill

class MySkill(BaseSkill):
    async def initialize(self, ctx): ...
    async def handle_event(self, event): ...
    async def handle_command(self, command): ...
    async def health_check(self): ...
    async def shutdown(self): ...
```

### TypeScript

```typescript
import { Skill } from '@agent-skills/sdk';

class MySkill implements Skill {
  async initialize(ctx: SkillContext): Promise<void> {}
  async handleEvent(event: SkillEvent): Promise<SkillResult> {}
  async handleCommand(command: SkillCommand): Promise<SkillResult> {}
  async healthCheck(): Promise<HealthStatus> {}
  async shutdown(): Promise<void> {}
}
```

## Skill Directory Layout

```
my-skill/
├── skill.yaml          # Manifest (required)
├── src/                # Source code
│   └── main.py         # Entry point (matches `entry` field)
├── tests/              # Test suite
├── scripts/            # Lifecycle hooks (optional)
└── README.md           # Documentation (optional)
```
