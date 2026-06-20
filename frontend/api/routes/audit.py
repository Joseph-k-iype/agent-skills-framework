from __future__ import annotations

from fastapi import APIRouter

from .. import audit as audit_log

router = APIRouter()


@router.get("")
def list_audit(limit: int = 200):
    return {"entries": audit_log.read(limit=limit)}
