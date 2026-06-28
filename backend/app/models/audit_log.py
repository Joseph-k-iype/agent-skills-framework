from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), default=None
    )
    action: Mapped[str] = mapped_column(index=True)  # 'SkillCreated', 'FolderMoved', ...
    resource_type: Mapped[str]
    resource_id: Mapped[str | None] = mapped_column(default=None)  # graph node id or pg uuid str
    workspace_id: Mapped[str | None] = mapped_column(default=None, index=True)
    trace_id: Mapped[str | None] = mapped_column(default=None)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
