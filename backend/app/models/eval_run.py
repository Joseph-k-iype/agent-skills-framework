from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class EvalRun(Base, TimestampMixin):
    """A persisted evaluation result, so dashboards can show trends over time.

    ``kind`` is ``fast`` (six-evaluator supervisor), ``deep`` (with/without
    effectiveness) or ``grade`` (interactive grade-vs-expected). ``score`` holds
    the headline number for that kind (overall / effectiveness_avg / pass_rate).
    """

    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(index=True)
    concept_path: Mapped[str] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(index=True)
    score: Mapped[float | None] = mapped_column(default=None)
    passed: Mapped[bool | None] = mapped_column(default=None)
    summary: Mapped[str | None] = mapped_column(default=None)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), default=None)
