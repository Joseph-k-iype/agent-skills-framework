"""API keys router — manage SDK keys (web UI, JWT-authed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.core.envelope import success
from app.schemas.marketplace import ApiKeyCreate
from app.services.api_key_service import ApiKeyService

router = APIRouter()


@router.get("")
async def list_keys(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return success(await ApiKeyService(db).list(user_id=user.id))


@router.post("")
async def create_key(
    body: ApiKeyCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # The full key is returned exactly once here.
    return success(await ApiKeyService(db).create(user_id=user.id, name=body.name))


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ApiKeyService(db).revoke(user_id=user.id, key_id=key_id)
    return success({"revoked": key_id})
