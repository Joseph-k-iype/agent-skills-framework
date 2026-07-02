"""Public marketplace — unauthenticated read-only catalog access.

These endpoints intentionally take NO auth dependency. They expose only
published, public listings and immutable version snapshots; never drafts or
workspace internals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.envelope import success
from app.services.marketplace_service import MarketplaceService

router = APIRouter()


@router.get("/marketplace")
async def public_list(
    q: str | None = None,
    type: str | None = None,
    category: str | None = None,
    capability: str | None = None,
    source: str | None = None,
    sort: str = "uses",
    limit: int = 60,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    # Clamp to bound query cost: at most 60 rows per page, non-negative offset.
    limit = max(1, min(60, limit))
    offset = max(0, offset)
    svc = MarketplaceService(db, None)
    return success(
        await svc.public_list(
            q=q,
            type=type,
            category=category,
            capability=capability,
            source=source,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/marketplace/categories")
async def public_categories(db: AsyncSession = Depends(get_db)):
    return success(await MarketplaceService(db, None).public_categories())


@router.get("/marketplace/{listing_id}")
async def public_get(listing_id: str, db: AsyncSession = Depends(get_db)):
    return success(await MarketplaceService(db, None).public_get(listing_id))


@router.get("/marketplace/{listing_id}/history")
async def public_history(
    listing_id: str, days: int = 90, db: AsyncSession = Depends(get_db)
):
    return success(await MarketplaceService(db, None).uses_history(listing_id, days=days))


@router.get("/skills/{sha}")
async def public_skill_by_sha(sha: str, db: AsyncSession = Depends(get_db)):
    return success(await MarketplaceService(db, None).public_fetch_by_sha(sha))
