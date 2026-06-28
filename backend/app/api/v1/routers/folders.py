"""Folders router (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.schemas.workspace import FolderCreate, FolderMove, FolderUpdate
from app.services.workspace_service import WorkspaceService

router = APIRouter()


@router.post("")
async def create_folder(
    body: FolderCreate,
    user: CurrentUser = Depends(require_permission("folder:create")),
    db: AsyncSession = Depends(get_db),
):
    folder = await WorkspaceService(db, user).create_folder(body)
    return success(folder.model_dump())


@router.get("/{folder_id}")
async def get_folder(
    folder_id: str,
    user: CurrentUser = Depends(require_permission("folder:read")),
    db: AsyncSession = Depends(get_db),
):
    folder = WorkspaceService(db, user).get_folder(folder_id)
    return success(folder.model_dump())


@router.patch("/{folder_id}")
async def rename_folder(
    folder_id: str,
    body: FolderUpdate,
    user: CurrentUser = Depends(require_permission("folder:update")),
    db: AsyncSession = Depends(get_db),
):
    folder = await WorkspaceService(db, user).rename_folder(folder_id, body)
    return success(folder.model_dump())


@router.post("/{folder_id}/move")
async def move_folder(
    folder_id: str,
    body: FolderMove,
    user: CurrentUser = Depends(require_permission("folder:update")),
    db: AsyncSession = Depends(get_db),
):
    folder = await WorkspaceService(db, user).move_folder(folder_id, body)
    return success(folder.model_dump())


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    user: CurrentUser = Depends(require_permission("folder:delete")),
    db: AsyncSession = Depends(get_db),
):
    await WorkspaceService(db, user).delete_folder(folder_id)
    return success({"deleted": folder_id})
