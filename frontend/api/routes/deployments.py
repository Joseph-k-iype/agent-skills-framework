from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from skill_sdk.registry import RegistryClient

from .. import audit as audit_log
from ..deps import get_registry, get_registry_path

router = APIRouter()


def _last_sync() -> str | None:
    for entry in audit_log.read(limit=500):
        if entry.get("action") == "Registry Synced" and entry.get("status") == "success":
            return entry.get("timestamp")
    return None


@router.get("")
def list_deployments(registry: RegistryClient = Depends(get_registry)):
    """Deployment targets derived from real registry state.

    The local registry is always a target; configured sources are additional
    targets. Status/last-sync come from real signals (path existence + the audit
    log), not fabricated values. Per-source skill attribution isn't tracked, so
    those counts are reported as null rather than invented.
    """
    skills = registry.list_skills()
    total = len(skills)
    last_sync = _last_sync()

    targets: list[dict] = [{
        "name": "Local Registry",
        "type": "local",
        "status": "active",
        "skillCount": total,
        "path": str(get_registry_path()),
        "lastSync": last_sync,
    }]

    index = registry._load_index()
    for src in index.get("sources", []):
        stype = src.get("type", "local")
        if stype == "local":
            p = src.get("path", "")
            status = "active" if p and Path(p).exists() else "error"
        else:
            status = "configured"
        targets.append({
            "name": src.get("url") or src.get("path") or f"{stype}-source",
            "type": stype,
            "status": status,
            "skillCount": None,  # not attributable per-source
            "url": src.get("url"),
            "path": src.get("path"),
            "ref": src.get("ref"),
            "lastSync": last_sync,
        })

    return {
        "targets": targets,
        "total_skills": total,
        "skills": [{"name": n, "latest": i.get("latest", "")} for n, i in skills.items()],
        "last_sync": last_sync,
    }
