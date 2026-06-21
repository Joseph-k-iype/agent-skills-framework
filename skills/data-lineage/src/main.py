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
    name = "data-lineage"
    version = "0.1.0"

    def __init__(self):
        self.pipeline_endpoint: str = ""
        self.lineage_store: str = ""

    async def initialize(self, ctx: SkillContext) -> None:
        self.pipeline_endpoint = ctx.config.get("pipeline_endpoint", "")
        self.lineage_store = ctx.config.get("lineage_store", "")
        self.logger = ctx.logger
        self.skill_id = ctx.state.get("skill_id", "")

    async def _trace_column_lineage(self, table: str, column: str) -> list[dict]:
        return [
            {"source": "raw_orders", "column": "order_id", "transform": "direct_map"},
            {"source": "raw_customers", "column": "customer_id", "transform": "join"},
        ]

    async def _build_lineage_graph(self, table: str) -> dict:
        return {
            "nodes": [
                {"id": "raw_orders", "type": "source"},
                {"id": "raw_customers", "type": "source"},
                {"id": "dim_orders", "type": "table"},
                {"id": "fact_sales", "type": "table"},
            ],
            "edges": [
                {"from": "raw_orders", "to": "dim_orders", "transform": "etl_job_1"},
                {"from": "raw_customers", "to": "dim_orders", "transform": "etl_job_1"},
                {"from": "dim_orders", "to": "fact_sales", "transform": "etl_job_2"},
            ],
        }

    async def _impact_analysis(self, table: str) -> list[str]:
        return ["fact_sales.revenue", "report.daily_sales", "dashboard.executive_summary"]

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        if event.name == "pipeline.completed":
            tables = event.payload.get("tables", [])
            return SkillResult(
                status="success",
                data={"traced": len(tables)},
                message=f"Traced lineage for {len(tables)} tables",
            )
        elif event.name == "schema.changed":
            table = event.payload.get("table", "")
            impacts = await self._impact_analysis(table)
            return SkillResult(
                status="success",
                data={"table": table, "impacted_assets": impacts},
                message=f"Schema change in {table} affects {len(impacts)} downstream assets",
            )
        return SkillResult(status="success", message=f"Handled event: {event.name}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        if command.name == "/trace":
            table = command.payload.get("table", "")
            column = command.payload.get("column", "")
            lineage = await self._trace_column_lineage(table, column)
            return SkillResult(
                status="success",
                data={"table": table, "column": column, "lineage": lineage},
                message=f"Traced lineage for {table}.{column}",
            )
        elif command.name == "/lineage-graph":
            table = command.payload.get("table", "")
            graph = await self._build_lineage_graph(table)
            return SkillResult(
                status="success",
                data={"graph": graph},
                message=f"Built lineage graph for {table}",
            )
        elif command.name == "/impact-analysis":
            table = command.payload.get("table", "")
            impacts = await self._impact_analysis(table)
            return SkillResult(
                status="success",
                data={"table": table, "impacted_assets": impacts},
                message=f"Impact analysis: {len(impacts)} downstream assets affected",
            )
        return SkillResult(status="error", error=f"Unknown command: {command.name}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            version=self.version,
            details={"lineage_store": self.lineage_store},
        )

    async def shutdown(self) -> None:
        pass
