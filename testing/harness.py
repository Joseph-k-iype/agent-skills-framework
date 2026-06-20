from __future__ import annotations

from pathlib import Path

from skill_sdk import SkillContext, SkillEvent, SkillCommand
from skill_sdk.validation import load_manifest


class SkillTestHarness:
    def __init__(self, skill_path: str | Path):
        self.skill_path = Path(skill_path).resolve()
        manifest_path = self.skill_path / "skill.yaml"
        if not manifest_path.exists():
            manifest_path = self.skill_path / "skill.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest found in {skill_path}")
        self.manifest = load_manifest(manifest_path)

    def create_context(self, overrides: dict | None = None) -> SkillContext:
        config = dict(self.manifest.get("config", {}).get("schema", {}))
        if overrides:
            config.update(overrides)
        return SkillContext(config=config)

    def make_event(self, name: str, payload: dict | None = None) -> SkillEvent:
        return SkillEvent(name=name, payload=payload or {})

    def make_command(self, name: str, args: list[str] | None = None) -> SkillCommand:
        return SkillCommand(name=name, args=args or [])
