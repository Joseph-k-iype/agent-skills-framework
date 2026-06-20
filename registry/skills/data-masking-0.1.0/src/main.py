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
    name = "data-masking"
    version = "0.1.0"

    def __init__(self):
        self.masking_policies: list[dict] = []
        self.pii_endpoint: str = ""

    async def initialize(self, ctx: SkillContext) -> None:
        self.masking_policies = ctx.config.get("masking_policies", [])
        self.pii_endpoint = ctx.config.get("pii_endpoint", "")
        self.logger = ctx.logger
        self.skill_id = ctx.state.get("skill_id", "")

    def _apply_mask(self, value: str, technique: str) -> str:
        if technique == "redact":
            return "***REDACTED***"
        elif technique == "tokenize":
            return f"tok_{hash(value) % 10**6:06d}"
        elif technique == "partial":
            return value[:2] + "****" + value[-2:] if len(value) > 4 else "****"
        return "****"

    async def _mask_dataset(self, dataset: dict, policy: dict) -> dict:
        fields = policy.get("fields", [])
        technique = policy.get("technique", "redact")
        masked = {}
        for field in fields:
            if field in dataset:
                masked[field] = self._apply_mask(str(dataset[field]), technique)
        return {"dataset_id": dataset.get("id", ""), "masked_fields": list(masked.keys()), "technique": technique}

    async def _discover_sensitive_fields(self, schema: dict) -> list[str]:
        sensitive = []
        pii_patterns = ["email", "ssn", "phone", "credit_card", "password", "address"]
        for col in schema.get("columns", []):
            col_name = col.get("name", "").lower()
            for pattern in pii_patterns:
                if pattern in col_name:
                    sensitive.append(col.get("name", ""))
                    break
        return sensitive

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        if event.name == "policy.updated":
            new_policy = event.payload.get("policy", {})
            self.masking_policies.append(new_policy)
            return SkillResult(
                status="success",
                data={"policies": len(self.masking_policies)},
                message=f"Added masking policy: {new_policy.get('name', 'unknown')}",
            )
        return SkillResult(status="success", message=f"Handled event: {event.name}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        if command.name == "/mask":
            dataset = command.payload.get("dataset", {})
            policy_name = command.payload.get("policy", "")
            policy = next((p for p in self.masking_policies if p.get("name") == policy_name), {})
            result = await self._mask_dataset(dataset, policy)
            return SkillResult(
                status="success",
                data={"result": result},
                message=f"Masked {len(result['masked_fields'])} fields using {policy_name or 'default'}",
            )
        elif command.name == "/discover-sensitive":
            schema = command.payload.get("schema", {})
            sensitive = await self._discover_sensitive_fields(schema)
            return SkillResult(
                status="success",
                data={"sensitive_fields": sensitive},
                message=f"Discovered {len(sensitive)} sensitive fields",
            )
        elif command.name == "/policies":
            return SkillResult(
                status="success",
                data={"policies": self.masking_policies},
                message=f"{len(self.masking_policies)} masking policies configured",
            )
        return SkillResult(status="error", error=f"Unknown command: {command.name}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            version=self.version,
            details={"policies_configured": len(self.masking_policies)},
        )

    async def shutdown(self) -> None:
        pass
