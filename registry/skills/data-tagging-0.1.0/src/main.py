from __future__ import annotations

from skill_sdk import (
    BaseSkill,
    SkillContext,
    SkillEvent,
    SkillCommand,
    SkillResult,
    HealthStatus,
)


class Skill(BaseSkill):
    name = "data-tagging"
    version = "0.1.0"

    def __init__(self):
        self.tag_rules: list[dict] = []
        self.tag_endpoint: str = ""

    async def initialize(self, ctx: SkillContext) -> None:
        self.tag_rules = ctx.config.get("tag_rules", [])
        self.tag_endpoint = ctx.config.get("tag_endpoint", "")
        self.logger = ctx.logger
        self.skill_id = ctx.state.get("skill_id", "")

    async def _resolve_tags(self, asset: dict) -> list[dict]:
        tags = []
        for rule in self.tag_rules:
            if _matches_rule(rule, asset):
                tags.append({"rule": rule.get("name", "unknown"), "tag": rule.get("tag", "")})
        return tags

    async def _propagate_tags(self, asset_id: str, tags: list[dict]) -> int:
        return len(tags)

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        if event.name == "asset.tagged":
            asset = event.payload.get("asset", {})
            tags = await self._resolve_tags(asset)
            propagated = await self._propagate_tags(asset.get("id", ""), tags)
            return SkillResult(
                status="success",
                data={"tags_applied": len(tags), "propagated": propagated},
                message=f"Applied {len(tags)} tags to {asset.get('name', 'unknown')}",
            )
        return SkillResult(status="success", message=f"Handled event: {event.name}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        if command.name == "/apply-tags":
            assets = command.payload.get("assets", [])
            total = 0
            for asset in assets:
                tags = await self._resolve_tags(asset)
                total += len(tags)
            return SkillResult(
                status="success",
                data={"assets_tagged": len(assets), "total_tags": total},
                message=f"Applied {total} tags across {len(assets)} assets",
            )
        elif command.name == "/list-tags":
            return SkillResult(
                status="success",
                data={"rules": self.tag_rules},
                message=f"{len(self.tag_rules)} tagging rules configured",
            )
        return SkillResult(status="error", error=f"Unknown command: {command.name}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            version=self.version,
            details={"rules_configured": len(self.tag_rules)},
        )

    async def shutdown(self) -> None:
        pass


def _matches_rule(rule: dict, asset: dict) -> bool:
    column_type = rule.get("column_type", "")
    if column_type and asset.get("type") == column_type:
        return True
    name_pattern = rule.get("name_pattern", "")
    if name_pattern and name_pattern in asset.get("name", ""):
        return True
    return False
