"""Knowledge / OKF router (Phase 2): import, search, documents, graph view."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.api.errors import NotFoundError
from app.core.envelope import success
from app.events.types import EventType
from app.schemas.knowledge import OkfImportRequest
from app.services.audit_service import AuditService
from app.services.knowledge_service import KnowledgeService
from app.services.okf_service import OkfService

router = APIRouter()


@router.post("/okf/import")
async def import_okf(
    body: OkfImportRequest,
    user: CurrentUser = Depends(require_permission("okf:import")),
    db: AsyncSession = Depends(get_db),
):
    result = await OkfService().ingest(
        source_repository=body.source_repository,
        workspace_id=body.workspace_id,
        folder_id=body.folder_id,
    )
    await AuditService(db).record(
        actor_id=user.id,
        action=EventType.OKF_IMPORTED,
        resource_type="OKFImport",
        workspace_id=body.workspace_id,
        payload={"documents": result.documents, "references": result.references},
    )
    return success(
        {
            "documents": result.documents,
            "references": result.references,
            "embedded": result.embedded,
            "orphans": result.orphans,
            "document_ids": result.document_ids,
        }
    )


@router.get("/search")
async def search(
    q: str = Query(min_length=1),
    k: int = Query(default=10, ge=1, le=50),
    _: CurrentUser = Depends(require_permission("search:read")),
):
    return success(await KnowledgeService().search(q, k))


@router.get("/documents")
async def list_documents(
    workspace_id: str | None = None,
    _: CurrentUser = Depends(require_permission("search:read")),
):
    return success(KnowledgeService().list_documents(workspace_id))


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    _: CurrentUser = Depends(require_permission("search:read")),
):
    doc = KnowledgeService().get_document(doc_id)
    if doc is None:
        raise NotFoundError("Document not found")
    return success(doc)


@router.get("/graph/{node_id}")
async def neighborhood(
    node_id: str,
    _: CurrentUser = Depends(require_permission("search:read")),
):
    data = KnowledgeService().neighborhood(node_id)
    if data is None:
        raise NotFoundError("Node not found")
    return success(data)
