"""Skills router (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.schemas.skill import SkillClone, SkillCreate, SkillPublish, SkillUpdate
from app.services.skill_service import SkillService

router = APIRouter()


@router.get("")
async def list_skills(
    workspace_id: str | None = None,
    folder_id: str | None = None,
    q: str | None = None,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    items = SkillService(db, user).list(workspace_id=workspace_id, folder_id=folder_id, q=q)
    return success([s.model_dump() for s in items])


@router.post("")
async def create_skill(
    body: SkillCreate,
    user: CurrentUser = Depends(require_permission("skill:create")),
    db: AsyncSession = Depends(get_db),
):
    return success((await SkillService(db, user).create(body)).model_dump())


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(SkillService(db, user).get(skill_id).model_dump())


@router.get("/{skill_id}/versions")
async def skill_versions(
    skill_id: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(SkillService(db, user).versions(skill_id).model_dump())


@router.patch("/{skill_id}")
async def update_skill(
    skill_id: str,
    body: SkillUpdate,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    return success((await SkillService(db, user).update(skill_id, body)).model_dump())


@router.post("/{skill_id}/publish")
async def publish_skill(
    skill_id: str,
    body: SkillPublish,
    user: CurrentUser = Depends(require_permission("skill:publish")),
    db: AsyncSession = Depends(get_db),
):
    return success((await SkillService(db, user).publish(skill_id, body)).model_dump())


@router.post("/{skill_id}/clone")
async def clone_skill(
    skill_id: str,
    body: SkillClone,
    user: CurrentUser = Depends(require_permission("skill:clone")),
    db: AsyncSession = Depends(get_db),
):
    return success((await SkillService(db, user).clone(skill_id, body)).model_dump())


@router.post("/{skill_id}/evaluate", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def evaluate_skill(
    skill_id: str,
    user: CurrentUser = Depends(require_permission("skill:evaluate")),
):
    # The Evaluator Supervisor arrives in Phase 6.
    return success({"skill_id": skill_id, "status": "queued"}, meta={"phase": "6"})


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    user: CurrentUser = Depends(require_permission("skill:delete")),
    db: AsyncSession = Depends(get_db),
):
    await SkillService(db, user).delete(skill_id)
    return success({"deleted": skill_id})
