"""Graph maintenance Celery tasks — implemented in later phases."""

from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="graph.rebuild_vector_index")
def rebuild_vector_index(label: str) -> dict:  # pragma: no cover
    raise NotImplementedError("Phase 2")
