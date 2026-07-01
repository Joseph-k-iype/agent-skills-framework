"""Marketplace router — browse the public catalog (web UI, JWT-authed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.services.marketplace_service import MarketplaceService

router = APIRouter()


class CloneRequest(BaseModel):
    workspace_id: str
    folder_path: str | None = None
    name: str | None = None
    version: int | None = None


@router.get("")
async def list_listings(
    q: str | None = None,
    type: str | None = None,
    capability: str | None = None,
    source: str | None = None,
    sort: str = "uses",
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(
        await MarketplaceService(db, user).list_listings(
            q=q, type=type, capability=capability, source=source, sort=sort
        )
    )


@router.get("/{listing_id}")
async def get_listing(
    listing_id: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(await MarketplaceService(db, user).get_listing(listing_id))


@router.post("/{listing_id}/clone")
async def clone_listing(
    listing_id: str,
    body: CloneRequest,
    user: CurrentUser = Depends(require_permission("skill:create")),
    db: AsyncSession = Depends(get_db),
):
    return success(
        await MarketplaceService(db, user).clone_to_workspace(
            listing_id=listing_id,
            workspace_id=body.workspace_id,
            folder_path=body.folder_path,
            name=body.name,
            version=body.version,
        )
    )
