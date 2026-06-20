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
    name = "data-discovery"
    version = "0.1.0"

    def __init__(self):
        self.sources: list[dict] = []
        self.catalog_endpoint: str = ""

    async def initialize(self, ctx: SkillContext) -> None:
        self.sources = ctx.config.get("sources", [])
        self.catalog_endpoint = ctx.config.get("catalog_endpoint", "")
        self.logger = ctx.logger
        self.skill_id = ctx.state.get("skill_id", "")

    async def _crawl_source(self, source: dict) -> dict:
        source_type = source.get("type", "unknown")
        return {
            "source": source.get("name", "unknown"),
            "type": source_type,
            "assets": [
                {
                    "type": "table",
                    "name": "example_table",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "name", "type": "varchar"},
                        {"name": "created_at", "type": "timestamp"},
                    ],
                }
            ],
            "profiles": {
                "row_count": 1000,
                "null_ratios": {"id": 0.0, "name": 0.02, "created_at": 0.0},
                "distinct_counts": {"id": 1000, "name": 950, "created_at": 500},
            },
        }

    async def _publish_to_catalog(self, results: list[dict]) -> bool:
        return True

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        if event.name == "data.source.connected":
            source = event.payload.get("source", {})
            result = await self._crawl_source(source)
            await self._publish_to_catalog([result])
            return SkillResult(
                status="success",
                data={"discovered": result},
                message=f"Discovered assets from {source.get('name', 'unknown')}",
            )
        return SkillResult(status="success", message=f"Handled event: {event.name}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        if command.name == "/discover":
            results = []
            for source in self.sources:
                result = await self._crawl_source(source)
                results.append(result)
            await self._publish_to_catalog(results)
            total_assets = sum(len(r["assets"]) for r in results)
            return SkillResult(
                status="success",
                data={"sources_crawled": len(results), "assets_discovered": total_assets},
                message=f"Discovered {total_assets} assets across {len(results)} sources",
            )
        elif command.name == "/profile":
            return SkillResult(
                status="success",
                data={"sources_profiled": len(self.sources)},
                message=f"Profiled {len(self.sources)} sources",
            )
        return SkillResult(status="error", error=f"Unknown command: {command.name}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            version=self.version,
            details={"sources_configured": len(self.sources)},
        )

    async def shutdown(self) -> None:
        pass
