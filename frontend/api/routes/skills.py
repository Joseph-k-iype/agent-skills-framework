from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from skill_sdk.registry import RegistryClient
from skill_sdk.validation import load_manifest, validate_manifest_file, validate_full_skill, ValidationError
from skill_sdk.hashing import compute_skill_id, validate_skill_id
from skill_sdk.adapter import generate_skill_doc

from ..deps import get_registry, get_registry_path

router = APIRouter()


class ValidateRequest(BaseModel):
    manifest: dict | None = None


class BuildRequest(BaseModel):
    path: str


class PublishRequest(BaseModel):
    path: str
    force: bool = False


@router.get("")
def list_skills(registry: RegistryClient = Depends(get_registry)):
    return registry.list_skills()


@router.get("/{name}")
def get_skill(name: str, registry: RegistryClient = Depends(get_registry)):
    try:
        info = registry.info(name)
        info["name"] = name
        return info
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/manifest")
def get_skill_manifest(name: str, registry: RegistryClient = Depends(get_registry)):
    try:
        info = registry.info(name)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))

    rel_path = info.get("locations", {}).get("local")
    if not rel_path:
        raise HTTPException(status_code=404, detail="Skill files not found locally")

    skill_dir = get_registry_path() / rel_path
    manifest_path = skill_dir / "skill.yaml"
    if not manifest_path.exists():
        manifest_path = skill_dir / "skill.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest file not found")

    try:
        manifest = load_manifest(manifest_path)
        raw = manifest_path.read_text(encoding="utf-8")
        return {"manifest": manifest, "raw": raw}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}/doc")
def get_skill_doc(name: str, format: str = "markdown", registry: RegistryClient = Depends(get_registry)):
    try:
        info = registry.info(name)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))

    rel_path = info.get("locations", {}).get("local")
    if not rel_path:
        raise HTTPException(status_code=404, detail="Skill files not found locally")

    skill_dir = get_registry_path() / rel_path
    manifest_path = skill_dir / "skill.yaml"
    if not manifest_path.exists():
        manifest_path = skill_dir / "skill.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")

    try:
        doc = generate_skill_doc(manifest_path, format=format)
        return {"doc": doc, "format": format, "name": name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}/versions")
def get_skill_versions(name: str, registry: RegistryClient = Depends(get_registry)):
    try:
        info = registry.info(name)
        return {
            "name": name,
            "versions": info.get("versions", []),
            "latest": info.get("latest", ""),
            "ids": info.get("ids", {}),
        }
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{name}/validate")
def validate_skill(name: str, registry: RegistryClient = Depends(get_registry)):
    try:
        info = registry.info(name)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))

    rel_path = info.get("locations", {}).get("local")
    if not rel_path:
        raise HTTPException(status_code=404, detail="Skill files not found locally")

    skill_dir = get_registry_path() / rel_path
    errors = validate_full_skill(skill_dir)
    return {"valid": len(errors) == 0, "errors": errors, "name": name}


@router.post("/{name}/verify")
def verify_skill(name: str, version: str | None = None, registry: RegistryClient = Depends(get_registry)):
    result = registry.verify(name, version)
    return result


@router.post("/build")
def build_skill(req: BuildRequest):
    target = Path(req.path).resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {target}")

    errors = validate_full_skill(target)
    if errors:
        return {"success": False, "errors": errors}

    manifest = load_manifest(target / "skill.yaml" if (target / "skill.yaml").exists() else target / "skill.json")
    name = manifest["name"]
    version = manifest["version"]

    skill_id = compute_skill_id(manifest, target)
    manifest["id"] = skill_id

    return {
        "success": True,
        "name": name,
        "version": version,
        "id": skill_id,
    }


@router.post("/publish")
def publish_skill(req: PublishRequest, registry: RegistryClient = Depends(get_registry)):
    target = Path(req.path).resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {target}")

    try:
        result = registry.publish(target, force=req.force)
        return {
            "success": True,
            "name": result["name"],
            "version": result["version"],
            "id": result["id"],
            "path": result["path"],
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
