"""Analytics router — insight dashboard data (eval trends, marketplace, graph)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    workspace_id: str | None = None,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(await AnalyticsService(db).overview(workspace_id=workspace_id))
