"""Insight dashboards — aggregate eval runs, marketplace activity and graph shape."""

from __future__ import annotations

from app.repositories.concept_graph_repo import ConceptGraphRepository
from app.repositories.eval_run_repo import EvalRunRepository
from app.repositories.marketplace_repo import MarketplaceRepository


class AnalyticsService:
    def __init__(self, db):
        self.db = db
        self.evals = EvalRunRepository(db)
        self.market = MarketplaceRepository(db)
        self.graph = ConceptGraphRepository()

    async def overview(self, *, workspace_id: str | None) -> dict:
        eval_summary = await self.evals.summary_by_kind(workspace_id=workspace_id)
        per_concept = await self.evals.per_concept(workspace_id=workspace_id)
        recent = await self.evals.recent(workspace_id=workspace_id, limit=15)
        most_installed = await self.market.most_installed(limit=8)

        graph = self.graph.analytics(workspace_id) if workspace_id else None

        return {
            "eval_summary": eval_summary,
            "eval_per_concept": per_concept,
            "eval_recent": [
                {
                    "workspace_id": r.workspace_id,
                    "concept_path": r.concept_path,
                    "kind": r.kind,
                    "score": r.score,
                    "summary": r.summary,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in recent
            ],
            "most_installed": [
                {
                    "title": x.title,
                    "version": x.version,
                    "downloads": x.downloads,
                    "type": x.type,
                }
                for x in most_installed
            ],
            "graph": graph,
        }
