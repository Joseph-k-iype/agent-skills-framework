"""Aggregate all v1 routers. Feature routers are added as they land."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    admin,
    analytics,
    api_keys,
    auth,
    concepts,
    folders,
    health,
    marketplace,
    public,
    sdk,
    taxonomy,
    workflows,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(
    concepts.router, prefix="/workspaces/{workspace_id}", tags=["concepts"]
)
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(sdk.router, prefix="/sdk", tags=["sdk"])
api_router.include_router(taxonomy.router, prefix="/taxonomy", tags=["taxonomy"])
