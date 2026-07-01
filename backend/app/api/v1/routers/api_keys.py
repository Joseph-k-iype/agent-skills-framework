"""API keys router — manage SDK keys (web UI, JWT-authed)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.core.envelope import success
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.marketplace_repo import MarketplaceRepository
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


@router.get("/{key_id}/usage")
async def get_key_usage(
    key_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated usage statistics for *key_id*, scoped to the calling user.

    404 is returned when the key does not exist OR is owned by someone else — we
    deliberately do not distinguish between the two cases to avoid leaking
    existence information (no 403).

    A revoked key still returns its historical usage rows; revocation does not
    delete events.
    """
    try:
        kid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="API key not found")

    key = await ApiKeyRepository(db).get_for_user(kid, uuid.UUID(user.id))
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    usage = await MarketplaceRepository(db).get_usage_for_key(kid)
    return success(usage)
