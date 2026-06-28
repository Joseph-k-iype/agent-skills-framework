"""OKF ingestion Celery task — wraps the same coroutine the API calls.

Use this for large or background imports; the synchronous API path covers small
knowledge sets. Run a worker with: ``make worker``.
"""

from __future__ import annotations

import asyncio

from app.services.okf_service import OkfService
from app.tasks.celery_app import celery_app


@celery_app.task(name="okf.ingest_repo")
def ingest_okf_repo(
    source_repository: str,
    workspace_id: str | None = None,
    folder_id: str | None = None,
) -> dict:
    result = asyncio.run(
        OkfService().ingest(
            source_repository=source_repository,
            workspace_id=workspace_id,
            folder_id=folder_id,
        )
    )
    return {
        "documents": result.documents,
        "references": result.references,
        "embedded": result.embedded,
        "orphans": result.orphans,
        "document_ids": result.document_ids,
    }
