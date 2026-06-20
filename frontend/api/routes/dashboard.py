from __future__ import annotations

from fastapi import APIRouter, Depends
from skill_sdk.registry import RegistryClient

from ..deps import get_registry

router = APIRouter()


@router.get("/stats")
def dashboard_stats(registry: RegistryClient = Depends(get_registry)):
    skills = registry.list_skills()
    all_versions = 0
    for info in skills.values():
        all_versions += len(info.get("versions", []))

    index = registry._load_index()
    sources_count = len(index.get("sources", []))

    return {
        "total_skills": len(skills),
        "total_versions": all_versions,
        "sources_count": sources_count,
        "latest_skills": skills,
    }
