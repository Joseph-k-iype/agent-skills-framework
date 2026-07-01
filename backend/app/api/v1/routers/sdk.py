"""SDK router — external skill consumption, authenticated by API key.

These endpoints are called by the `eakso` Python SDK (and any programmatic
client) with ``Authorization: Bearer sk_live_…``, not the web JWT.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_api_key
from app.core.envelope import success
from app.schemas.marketplace import UsageBody
from app.services.marketplace_service import MarketplaceService

router = APIRouter()


@router.get("/skill/{listing_id}")
async def fetch_skill(
    listing_id: str,
    user: CurrentUser = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    out = await MarketplaceService(db, user).fetch_skill(
        listing_id=listing_id, user_id=user.id, api_key_id=user.api_key_id
    )
    return success(out)


@router.post("/usage")
async def report_usage(
    body: UsageBody,
    user: CurrentUser = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    out = await MarketplaceService(db, user).report_usage(
        listing_id=body.listing_id,
        user_id=user.id,
        kind=body.kind,
        meta=body.meta,
        api_key_id=user.api_key_id,
    )
    return success(out)
