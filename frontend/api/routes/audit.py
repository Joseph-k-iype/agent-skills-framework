from __future__ import annotations

from fastapi import APIRouter, Query

from .. import audit as audit_log

router = APIRouter()


@router.get("")
def list_audit(limit: int = Query(200, ge=1, le=1000)):
    return {"entries": audit_log.read(limit=limit)}
