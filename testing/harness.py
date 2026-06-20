from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from skill_sdk import (
    BaseSkill,
    SkillContext,
    SkillEvent,
    SkillCommand,
    SkillResult,
    HealthStatus,
)
from skill_sdk.validation import load_manifest


class SkillTestHarness:
    """Load a skill from disk and drive its lifecycle in isolation.

    Beyond building contexts/events, the harness can import the skill's entry
    point, instantiate its :class:`BaseSkill`, and run the async lifecycle so
    tests exercise real behaviour instead of hand-rolling all of this.
    """

    def __init__(self, skill_path: str | Path):
        self.skill_path = Path(skill_path).resolve()
        manifest_path = self.skill_path / "skill.yaml"
        if not manifest_path.exists():
            manifest_path = self.skill_path / "skill.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest found in {skill_path}")
        self.manifest = load_manifest(manifest_path)
        self._skill: BaseSkill | None = None

    # -- context / message factories ---------------------------------------

    def create_context(self, overrides: dict | None = None) -> SkillContext:
        config = dict(self.manifest.get("config", {}).get("schema", {}))
        if overrides:
            config.update(overrides)
        return SkillContext(config=config)

    def make_event(self, name: str, payload: dict | None = None) -> SkillEvent:
        return SkillEvent(name=name, payload=payload or {})

    def make_command(self, name: str, args: list[str] | None = None) -> SkillCommand:
        return SkillCommand(name=name, args=args or [])

    # -- loading / running -------------------------------------------------

    def load_skill(self) -> BaseSkill:
        """Import the manifest's entry point and instantiate its BaseSkill."""
        entry = self.manifest.get("entry", "")
        entry_path = (self.skill_path / entry).resolve()
        if not entry_path.exists():
            raise FileNotFoundError(f"Entry point not found: {entry_path}")

        mod_name = f"_skill_under_test_{abs(hash(str(entry_path)))}"
        spec = importlib.util.spec_from_file_location(mod_name, entry_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load entry point {entry_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)

        skill_cls = None
        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseSkill)
                and obj is not BaseSkill
            ):
                skill_cls = obj
                break
        if skill_cls is None:
            raise TypeError(f"No BaseSkill subclass found in {entry_path}")
        self._skill = skill_cls()
        return self._skill

    @property
    def skill(self) -> BaseSkill:
        if self._skill is None:
            return self.load_skill()
        return self._skill

    async def initialize(self, config_overrides: dict | None = None) -> SkillContext:
        ctx = self.create_context(config_overrides)
        await self.skill.initialize(ctx)
        return ctx

    async def run_command(self, name: str, args: list[str] | None = None) -> SkillResult:
        return await self.skill.handle_command(self.make_command(name, args))

    async def run_event(self, name: str, payload: dict | None = None) -> SkillResult:
        return await self.skill.handle_event(self.make_event(name, payload))

    async def health(self) -> HealthStatus:
        return await self.skill.health_check()

    async def shutdown(self) -> None:
        await self.skill.shutdown()
