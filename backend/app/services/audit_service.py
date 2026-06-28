"""Records an audit row and publishes the matching domain event in one call."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import current_trace_id
from app.events.bus import publish
from app.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self.repo = AuditRepository(db)

    async def record(
        self,
        *,
        actor_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        workspace_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        payload = payload or {}
        await self.repo.add(
            actor_id=uuid.UUID(actor_id) if actor_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            workspace_id=workspace_id,
            trace_id=current_trace_id(),
            payload=payload,
        )
        await publish(
            action,
            {"resource_id": resource_id, "workspace_id": workspace_id, "actor": actor_id, **payload},
        )
