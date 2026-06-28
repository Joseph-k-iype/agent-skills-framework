"""OKF ingestion Celery tasks — implemented in Phase 2."""

from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="okf.ingest_repo")
def ingest_okf_repo(source_repository: str, target_folder_id: str) -> dict:  # pragma: no cover
    raise NotImplementedError("Phase 2")
