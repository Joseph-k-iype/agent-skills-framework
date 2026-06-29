"""Concepts router — OKF markdown files (skills/agents/prompts/docs).

A concept is addressed by ``workspace_id`` + repo-relative ``path`` (passed as a
query parameter so paths with slashes are unambiguous). Reuses the ``skill:*``
permission codes — a skill is just a concept with ``type: skill``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.schemas.concept import (
    ConceptCreate,
    ConceptMove,
    ConceptPublish,
    ConceptUpdate,
)
from app.services.concept_service import ConceptService

router = APIRouter()


@router.get("/concepts")
async def list_concepts(
    workspace_id: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    items = ConceptService(db, user).list_concepts(workspace_id)
    return success([c.model_dump() for c in items])


@router.post("/concepts")
async def create_concept(
    workspace_id: str,
    body: ConceptCreate,
    user: CurrentUser = Depends(require_permission("skill:create")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).create(
        workspace_id=workspace_id,
        folder_path=body.folder_path,
        name=body.name,
        type=body.type,
        description=body.description,
        runtime=body.runtime,
        tags=body.tags,
        capabilities=body.capabilities,
        body=body.body,
        frontmatter=body.frontmatter,
    )
    return success(out.model_dump())


@router.get("/concept")
async def get_concept(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).get(workspace_id, path).model_dump())


@router.put("/concept")
async def update_concept(
    workspace_id: str,
    path: str,
    body: ConceptUpdate,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).update(
        workspace_id=workspace_id,
        path=path,
        title=body.title,
        type=body.type,
        description=body.description,
        runtime=body.runtime,
        tags=body.tags,
        capabilities=body.capabilities,
        body=body.body,
        frontmatter=body.frontmatter,
    )
    return success(out.model_dump())


@router.delete("/concept")
async def delete_concept(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:delete")),
    db: AsyncSession = Depends(get_db),
):
    await ConceptService(db, user).delete(workspace_id=workspace_id, path=path)
    return success({"deleted": path})


@router.post("/concept/move")
async def move_concept(
    workspace_id: str,
    path: str,
    body: ConceptMove,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).move(
        workspace_id=workspace_id, src_path=path, dst_folder_path=body.dst_folder_path
    )
    return success(out.model_dump())


@router.get("/concept/history")
async def concept_history(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    items = ConceptService(db, user).history(workspace_id, path)
    return success([v.model_dump() for v in items])


@router.post("/concept/publish")
async def publish_concept(
    workspace_id: str,
    path: str,
    body: ConceptPublish,
    user: CurrentUser = Depends(require_permission("skill:publish")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).publish(
        workspace_id=workspace_id, path=path, version=body.version
    )
    return success(out.model_dump())


@router.post("/concept/evaluate")
async def evaluate_concept(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:evaluate")),
    db: AsyncSession = Depends(get_db),
):
    report = await ConceptService(db, user).evaluate(workspace_id, path)
    return success(report)


@router.get("/search")
async def search_workspace(
    workspace_id: str,
    q: str,
    k: int = 10,
    user: CurrentUser = Depends(require_permission("search:read")),
    db: AsyncSession = Depends(get_db),
):
    results = await ConceptService(db, user).search(workspace_id, q, k)
    return success(results)
