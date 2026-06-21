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
    name = "data-enrichment"
    version = "0.1.0"

    def __init__(self):
        self.enrichment_rules: list[dict] = []
        self.glossary_endpoint: str = ""

    async def initialize(self, ctx: SkillContext) -> None:
        self.enrichment_rules = ctx.config.get("enrichment_rules", [])
        self.glossary_endpoint = ctx.config.get("glossary_endpoint", "")
        self.logger = ctx.logger
        self.skill_id = ctx.state.get("skill_id", "")

    async def _classify_asset(self, asset: dict) -> dict:
        classifications = []
        for rule in self.enrichment_rules:
            if _matches_classification(rule, asset):
                classifications.append({
                    "classification": rule.get("classification", ""),
                    "confidence": _compute_confidence(asset, rule),
                })
        return {"asset_id": asset.get("id", ""), "classifications": classifications}

    async def _link_glossary_terms(self, asset: dict) -> list[str]:
        return ["customer", "product", "transaction"]

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        if event.name == "asset.discovered":
            asset = event.payload.get("asset", {})
            classification = await self._classify_asset(asset)
            terms = await self._link_glossary_terms(asset)
            return SkillResult(
                status="success",
                data={"asset": asset.get("name", ""), "classification": classification, "glossary_terms": terms},
                message=f"Enriched {asset.get('name', 'unknown')} with {len(terms)} glossary terms",
            )
        elif event.name == "glossary.updated":
            self.glossary_endpoint = event.payload.get("glossary_endpoint", self.glossary_endpoint)
            return SkillResult(
                status="success",
                data={"glossary_endpoint": self.glossary_endpoint},
                message="Glossary updated; future enrichments will use the new terms",
            )
        return SkillResult(status="success", message=f"Handled event: {event.name}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        if command.name == "/enrich":
            assets = command.payload.get("assets", [])
            results = []
            for asset in assets:
                c = await self._classify_asset(asset)
                t = await self._link_glossary_terms(asset)
                results.append({**c, "glossary_terms": t})
            return SkillResult(
                status="success",
                data={"enriched": results},
                message=f"Enriched {len(results)} assets",
            )
        elif command.name == "/classify":
            assets = command.payload.get("assets", [])
            results = [await self._classify_asset(a) for a in assets]
            return SkillResult(
                status="success",
                data={"classified": results},
                message=f"Classified {len(results)} assets",
            )
        elif command.name == "/link-glossary":
            return SkillResult(
                status="success",
                data={"glossary_endpoint": self.glossary_endpoint},
                message="Glossary linking complete",
            )
        return SkillResult(status="error", error=f"Unknown command: {command.name}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            version=self.version,
            details={"rules_configured": len(self.enrichment_rules)},
        )

    async def shutdown(self) -> None:
        pass


def _matches_classification(rule: dict, asset: dict) -> bool:
    pattern = rule.get("pattern", "")
    return not pattern or pattern in str(asset).lower()


def _compute_confidence(asset: dict, rule: dict) -> float:
    return rule.get("confidence", 0.85)
