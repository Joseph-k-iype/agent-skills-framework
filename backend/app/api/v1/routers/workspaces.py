"""Workspaces router (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services.workspace_service import WorkspaceService

router = APIRouter()


@router.get("")
async def list_workspaces(
    user: CurrentUser = Depends(require_permission("workspace:read")),
    db: AsyncSession = Depends(get_db),
):
    items = WorkspaceService(db, user).list_workspaces()
    return success([w.model_dump() for w in items])


@router.post("")
async def create_workspace(
    body: WorkspaceCreate,
    user: CurrentUser = Depends(require_permission("workspace:create")),
    db: AsyncSession = Depends(get_db),
):
    ws = await WorkspaceService(db, user).create_workspace(body)
    return success(ws.model_dump())


@router.get("/{workspace_id}")
async def get_workspace_tree(
    workspace_id: str,
    user: CurrentUser = Depends(require_permission("workspace:read")),
    db: AsyncSession = Depends(get_db),
):
    tree = WorkspaceService(db, user).get_tree(workspace_id)
    return success(tree.model_dump())


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    user: CurrentUser = Depends(require_permission("workspace:update")),
    db: AsyncSession = Depends(get_db),
):
    ws = await WorkspaceService(db, user).update_workspace(workspace_id, body)
    return success(ws.model_dump())


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    user: CurrentUser = Depends(require_permission("workspace:delete")),
    db: AsyncSession = Depends(get_db),
):
    await WorkspaceService(db, user).delete_workspace(workspace_id)
    return success({"deleted": workspace_id})
