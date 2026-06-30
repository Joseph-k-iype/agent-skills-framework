"""Best-effort persistence of eval runs (for insight dashboards).

Runs in its own DB session so a persistence hiccup never poisons the request
session or breaks the eval response. Fire-and-forget from the eval endpoints.
"""

from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import EvalRun

log = get_logger("eval.history")


async def record_eval_run(
    *,
    workspace_id: str,
    concept_path: str,
    kind: str,
    score: float | None,
    passed: bool | None = None,
    summary: str | None = None,
    payload: dict | None = None,
    actor_id: str | None = None,
) -> None:
    try:
        actor = uuid.UUID(actor_id) if actor_id else None
    except (ValueError, TypeError):
        actor = None
    try:
        async with SessionLocal() as session:
            session.add(
                EvalRun(
                    workspace_id=workspace_id,
                    concept_path=concept_path,
                    kind=kind,
                    score=score,
                    passed=passed,
                    summary=summary,
                    payload=payload or {},
                    actor_id=actor,
                )
            )
            await session.commit()
    except Exception as exc:  # never break the eval response over telemetry
        log.warning("eval_run_persist_failed", kind=kind, error=str(exc))
