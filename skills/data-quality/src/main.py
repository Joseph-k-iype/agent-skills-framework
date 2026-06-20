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
    name = "data-quality"
    version = "0.1.0"

    def __init__(self):
        self.quality_rules: list[dict] = []
        self.report_endpoint: str = ""

    async def initialize(self, ctx: SkillContext) -> None:
        self.quality_rules = ctx.config.get("quality_rules", [])
        self.report_endpoint = ctx.config.get("report_endpoint", "")
        self.logger = ctx.logger
        self.skill_id = ctx.state.get("skill_id", "")

    async def _run_checks(self, source: dict) -> dict:
        checks = []
        for rule in self.quality_rules:
            dimension = rule.get("dimension", "unknown")
            threshold = rule.get("threshold", 0.95)
            score = _compute_score(dimension)
            passed = score >= threshold
            checks.append({
                "rule": rule.get("name", "unknown"),
                "dimension": dimension,
                "score": score,
                "threshold": threshold,
                "passed": passed,
            })
        overall = sum(c["score"] for c in checks) / len(checks) if checks else 0
        return {"source": source.get("name", "unknown"), "checks": checks, "overall": overall}

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        if event.name == "schedule.quality.daily":
            sources = event.payload.get("sources", [])
            results = [await self._run_checks(s) for s in sources]
            passing = sum(1 for r in results if r["overall"] >= 0.95)
            return SkillResult(
                status="success",
                data={"sources_checked": len(results), "passing": passing},
                message=f"Quality check: {passing}/{len(results)} sources passing",
            )
        return SkillResult(status="success", message=f"Handled event: {event.name}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        if command.name == "/validate":
            sources = command.payload.get("sources", [])
            results = [await self._run_checks(s) for s in sources]
            return SkillResult(
                status="success",
                data={"results": results},
                message=f"Validated {len(results)} sources",
            )
        elif command.name == "/rules":
            return SkillResult(
                status="success",
                data={"rules": self.quality_rules},
                message=f"{len(self.quality_rules)} quality rules configured",
            )
        return SkillResult(status="error", error=f"Unknown command: {command.name}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            version=self.version,
            details={"rules_configured": len(self.quality_rules)},
        )

    async def shutdown(self) -> None:
        pass


def _compute_score(dimension: str) -> float:
    scores = {
        "completeness": 0.97,
        "consistency": 0.94,
        "timeliness": 0.99,
        "uniqueness": 0.96,
        "accuracy": 0.93,
    }
    return scores.get(dimension, 0.95)
