"""Workflows router — Phase 4 stub (reserved)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.envelope import success

router = APIRouter()


@router.get("")
async def list_workflows():
    """Placeholder until the Workflow Builder phase."""
    return success([], meta={"phase": "4", "status": "not_implemented"})
