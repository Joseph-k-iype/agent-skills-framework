"""Background reindex task — rebuild a workspace's FalkorDB projection from files.

The API path reindexes synchronously per file on save; this task is for rebuilding
a whole workspace's projection (e.g. after a bulk git operation). Run a worker
with ``make worker``.
"""

from __future__ import annotations

import asyncio

from app.services.index_service import IndexService
from app.tasks.celery_app import celery_app


@celery_app.task(name="index.reindex_workspace")
def reindex_workspace(workspace_id: str) -> dict:
    result = asyncio.run(IndexService().reindex_workspace(workspace_id))
    return {
        "documents": result.documents,
        "references": result.references,
        "embedded": result.embedded,
        "orphans": result.orphans,
    }
