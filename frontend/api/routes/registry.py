from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from skill_sdk.registry import RegistryClient

from .. import audit
from ..deps import get_registry
from ..security import require_api_key, workspace_root, auth_enabled, resolve_in_workspace

router = APIRouter()


class AddSourceRequest(BaseModel):
    type: str
    url: str | None = None
    path: str | None = None
    ref: str = "main"
    cache: str | None = None


@router.get("")
def registry_info(registry: RegistryClient = Depends(get_registry)):
    index = registry._load_index()
    return {
        "schema_version": index.get("schema_version", 1),
        "sources": index.get("sources", []),
        "skill_count": len(index.get("skills", {})),
        # Surface the *real* server configuration so the UI stops claiming
        # values that don't match the backend.
        "auto_tag": bool(getattr(registry, "auto_tag", False)),
        "workspace": str(workspace_root()),
        "auth_required": auth_enabled(),
    }


@router.get("/sources")
def list_sources(registry: RegistryClient = Depends(get_registry)):
    index = registry._load_index()
    return index.get("sources", [])


@router.post("/sources", dependencies=[Depends(require_api_key)])
def add_source(req: AddSourceRequest, registry: RegistryClient = Depends(get_registry)):
    if req.type not in ("local", "git"):
        raise HTTPException(status_code=400, detail="source type must be 'local' or 'git'")
    config: dict = {"type": req.type}
    if req.type == "git":
        if not req.url:
            raise HTTPException(status_code=400, detail="git source requires a url")
        config["url"] = req.url
        config["ref"] = req.ref
    else:
        if not req.path:
            raise HTTPException(status_code=400, detail="local source requires a path")
        # Confine local source paths to the workspace sandbox.
        config["path"] = str(resolve_in_workspace(req.path))
    if req.cache:
        config["cache"] = str(resolve_in_workspace(req.cache))
    result = registry.add_source(config)
    audit.record("Source Added", details=f"{req.type}: {req.url or config.get('path')}")
    return result


@router.post("/sync", dependencies=[Depends(require_api_key)])
def sync_registry(registry: RegistryClient = Depends(get_registry)):
    result = registry.sync_from_sources()
    audit.record(
        "Registry Synced",
        status="error" if result.get("errors") else "success",
        details=f"{result.get('synced', 0)} skill(s); {len(result.get('errors', []))} error(s)",
    )
    return result
