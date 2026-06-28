"""Audit log persistence (PostgreSQL)."""

from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        workspace_id: str | None,
        trace_id: str | None,
        payload: dict,
    ) -> AuditLog:
        row = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            workspace_id=workspace_id,
            trace_id=trace_id,
            payload=payload,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def recent(self, limit: int = 100) -> list[AuditLog]:
        return list(
            (
                await self.db.execute(select(AuditLog).order_by(desc(AuditLog.occurred_at)).limit(limit))
            ).scalars()
        )
