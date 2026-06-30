"""Eval-run persistence + analytics aggregation (PostgreSQL)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EvalRun


class EvalRunRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(
        self,
        *,
        workspace_id: str,
        concept_path: str,
        kind: str,
        score: float | None,
        passed: bool | None,
        summary: str | None,
        payload: dict,
        actor_id: uuid.UUID | None,
    ) -> EvalRun:
        row = EvalRun(
            workspace_id=workspace_id,
            concept_path=concept_path,
            kind=kind,
            score=score,
            passed=passed,
            summary=summary,
            payload=payload,
            actor_id=actor_id,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def recent(self, *, workspace_id: str | None, limit: int = 50) -> list[EvalRun]:
        stmt = select(EvalRun).order_by(EvalRun.created_at.desc()).limit(limit)
        if workspace_id:
            stmt = stmt.where(EvalRun.workspace_id == workspace_id)
        return list((await self.db.scalars(stmt)).all())

    async def summary_by_kind(self, *, workspace_id: str | None) -> list[dict]:
        """Per-kind run count + average score (for dashboard cards)."""
        stmt = select(
            EvalRun.kind,
            func.count(EvalRun.id),
            func.avg(EvalRun.score),
        ).group_by(EvalRun.kind)
        if workspace_id:
            stmt = stmt.where(EvalRun.workspace_id == workspace_id)
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "kind": k,
                "runs": int(n),
                "avg_score": round(float(avg), 2) if avg is not None else None,
            }
            for k, n, avg in rows
        ]

    async def per_concept(self, *, workspace_id: str | None, limit: int = 20) -> list[dict]:
        """Latest score per concept+kind, for the per-skill effectiveness table."""
        stmt = (
            select(
                EvalRun.concept_path,
                EvalRun.kind,
                func.count(EvalRun.id),
                func.avg(EvalRun.score),
            )
            .group_by(EvalRun.concept_path, EvalRun.kind)
            .order_by(func.count(EvalRun.id).desc())
            .limit(limit)
        )
        if workspace_id:
            stmt = stmt.where(EvalRun.workspace_id == workspace_id)
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "concept_path": p,
                "kind": k,
                "runs": int(n),
                "avg_score": round(float(avg), 2) if avg is not None else None,
            }
            for p, k, n, avg in rows
        ]
