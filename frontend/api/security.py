from __future__ import annotations

import os
from pathlib import Path

from fastapi import Header, HTTPException

# Treated as a shared/hosted service: every endpoint that accepts a server-side
# filesystem path MUST route it through ``resolve_in_workspace`` so a caller can
# never read/write/publish outside the configured workspace root (no traversal,
# no absolute escape).

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ENV = "SKILLS_WORKSPACE"
API_KEY_ENV = "SKILLS_API_KEY"


def workspace_root() -> Path:
    root = Path(os.environ.get(WORKSPACE_ENV, _PROJECT_ROOT / "workspace")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_in_workspace(p: str) -> Path:
    """Resolve a user-supplied path, confined to the workspace root.

    Relative paths are joined to the root; absolute paths must already live
    inside it. Anything that escapes (``..``, a different absolute prefix,
    symlink target outside) is rejected with HTTP 400.
    """
    if not p or not str(p).strip():
        raise HTTPException(status_code=400, detail="Path is required")
    root = workspace_root()
    raw = Path(p)
    candidate = (raw if raw.is_absolute() else root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(
            status_code=400,
            detail=f"Path '{p}' escapes the workspace root ({root}).",
        )
    return candidate


def auth_enabled() -> bool:
    return bool(os.environ.get(API_KEY_ENV))


def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Opt-in API-key gate for mutating endpoints.

    When ``SKILLS_API_KEY`` is unset the gate is disabled (local dev). In a
    hosted deployment set the env var and send it as ``X-API-Key`` or
    ``Authorization: Bearer <key>``. NOTE: the frontend role switcher is a UX
    preview only — it is NOT an authorization boundary. Real per-user authz is
    an explicit, documented gap (see docs/security.md).
    """
    expected = os.environ.get(API_KEY_ENV)
    if not expected:
        return
    provided = x_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
