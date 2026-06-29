"""Aggregate all v1 routers. Feature routers are added as they land."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    admin,
    auth,
    concepts,
    folders,
    health,
    knowledge,
    skills,
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
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
