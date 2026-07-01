"""SDK router — external skill consumption, authenticated by API key.

These endpoints are called by the `eakso` Python SDK (and any programmatic
client) with ``Authorization: Bearer sk_live_…``, not the web JWT.

``GET /sdk/download`` is intentionally PUBLIC (no auth) — it serves the
client library so anyone can bootstrap without a key.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_api_key
from app.core.envelope import success
from app.schemas.marketplace import UsageBody
from app.services.marketplace_service import MarketplaceService

router = APIRouter()


# ---------------------------------------------------------------------------
# Path resolver — small function so tests can monkeypatch it.
# ---------------------------------------------------------------------------

def _resolve_dist_dir() -> Path:
    """Return the absolute path to sdk/python/dist/ relative to the repo root.

    Resolution: walk up from this file's location until we find the repo root
    (identified by the presence of ``sdk/python/dist`` or, failing that, the
    nearest directory that contains a ``backend/`` child).
    """
    here = Path(__file__).resolve()
    # Walk upward looking for the repo root (contains sdk/ sibling of backend/)
    for parent in here.parents:
        candidate = parent / "sdk" / "python" / "dist"
        if (parent / "backend").is_dir() and (parent / "sdk").is_dir():
            return candidate
    # Fallback: go four levels up from this file (routers/ → v1/ → api/ → app/ → backend/ → repo root)
    return here.parents[5] / "sdk" / "python" / "dist"


# ---------------------------------------------------------------------------
# Public download — no auth dependency
# ---------------------------------------------------------------------------

@router.get("/download")
async def download_sdk():
    """Serve the newest built SDK wheel/sdist from ``sdk/python/dist/``.

    Returns:
        200 FileResponse with ``X-Checksum-SHA256`` header and attachment
        ``Content-Disposition``.
        503 JSON ``{"ok": false, "reason": ...}`` when the artifact is absent.
    """
    dist_dir = _resolve_dist_dir()

    # Check for missing or empty dist directory.
    if not dist_dir.exists() or not dist_dir.is_dir():
        return JSONResponse(
            status_code=503,
            content={"ok": False, "reason": "SDK artifact not built"},
        )

    artifacts = sorted(dist_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not artifacts:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "reason": "SDK artifact not built"},
        )

    newest = artifacts[0]
    sha256 = hashlib.sha256(newest.read_bytes()).hexdigest()

    return FileResponse(
        path=str(newest),
        media_type="application/octet-stream",
        filename=newest.name,
        headers={
            "X-Checksum-SHA256": sha256,
            "Content-Disposition": f'attachment; filename="{newest.name}"',
        },
    )


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
