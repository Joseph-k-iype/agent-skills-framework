from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from skill_sdk.registry import RegistryClient
from skill_sdk.validation import ValidationError

from ..deps import get_registry

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
    }


@router.get("/sources")
def list_sources(registry: RegistryClient = Depends(get_registry)):
    index = registry._load_index()
    return index.get("sources", [])


@router.post("/sources")
def add_source(req: AddSourceRequest, registry: RegistryClient = Depends(get_registry)):
    config = {"type": req.type}
    if req.url:
        config["url"] = req.url
        config["ref"] = req.ref
    if req.path:
        config["path"] = req.path
    if req.cache:
        config["cache"] = req.cache
    result = registry.add_source(config)
    return result


@router.post("/sync")
def sync_registry(registry: RegistryClient = Depends(get_registry)):
    result = registry.sync_from_sources()
    return result
