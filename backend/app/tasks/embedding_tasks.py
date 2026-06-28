"""Embedding generation Celery tasks — implemented in Phase 2."""

from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="embedding.generate")
def generate_embedding(node_label: str, node_id: str, text: str) -> dict:  # pragma: no cover
    raise NotImplementedError("Phase 2")
