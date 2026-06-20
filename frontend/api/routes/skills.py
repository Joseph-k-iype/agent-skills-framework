from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from skill_sdk.registry import RegistryClient
from skill_sdk.validation import (
    load_manifest,
    load_manifest_with_body,
    validate_full_skill,
    lint_full_skill,
    ValidationError,
)
from skill_sdk.hashing import compute_skill_id
from skill_sdk.versioning import SemVer
from skill_sdk.adapter import generate_skill_doc

from .. import audit
from ..deps import get_registry, get_registry_path
from ..security import resolve_in_workspace, require_api_key

router = APIRouter()


class BuildRequest(BaseModel):
    path: str


class PublishRequest(BaseModel):
    path: str
    force: bool = False


class InstallRequest(BaseModel):
    version: str | None = None
    target: str | None = None
    verify: bool = True


class ScaffoldRequest(BaseModel):
    manifest: dict
    files: dict[str, str] | None = None
    publish: bool = False
    force: bool = False


def _manifest_path(skill_dir: Path) -> Path | None:
    for fname in ("SKILL.md", "skill.yaml", "skill.yml", "skill.json"):
        p = skill_dir / fname
        if p.exists():
            return p
    return None


def _sorted_versions(versions: list[str]) -> list[str]:
    """Ascending SemVer order; unparseable versions sink to the end."""
    parseable = sorted((v for v in versions if _is_semver(v)), key=SemVer)
    rest = sorted(v for v in versions if not _is_semver(v))
    return parseable + rest


def _is_semver(v: str) -> bool:
    try:
        SemVer(v)
        return True
    except ValueError:
        return False


@router.get("")
def list_skills(registry: RegistryClient = Depends(get_registry)):
    return registry.list_skills()


@router.get("/compliance")
def skills_compliance(registry: RegistryClient = Depends(get_registry)):
    """One-shot compliance summary for every skill (avoids the UI's N+1 calls)."""
    out = []
    for name, info in registry.list_skills().items():
        entry = registry.info(name)
        rel = entry.get("locations", {}).get("local")
        runtime = ""
        permissions = 0
        capabilities = 0
        valid = None
        errors: list[str] = []
        if rel:
            skill_dir = get_registry_path() / rel
            errors = validate_full_skill(skill_dir)
            valid = len(errors) == 0
            mpath = _manifest_path(skill_dir)
            if mpath:
                try:
                    m = load_manifest(mpath)
                    runtime = m.get("runtime", "")
                    permissions = len(m.get("permissions", []) or [])
                    capabilities = len(m.get("capabilities", []) or [])
                except ValidationError:
                    pass
        out.append({
            "name": name,
            "latest": info.get("latest", ""),
            "runtime": runtime,
            "valid": valid,
            "permissions": permissions,
            "capabilities": capabilities,
            "errors": errors,
        })
    return {"skills": out}


@router.get("/{name}")
def get_skill(name: str, registry: RegistryClient = Depends(get_registry)):
    try:
        info = dict(registry.info(name))
        info["name"] = name
        return info
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/manifest")
def get_skill_manifest(name: str, registry: RegistryClient = Depends(get_registry)):
    skill_dir = _skill_dir_or_404(name, registry)
    manifest_path = _manifest_path(skill_dir)
    if not manifest_path:
        raise HTTPException(status_code=404, detail="Manifest file not found")
    try:
        manifest, body = load_manifest_with_body(manifest_path)
        raw = manifest_path.read_text(encoding="utf-8")
        return {"manifest": manifest, "body": body, "raw": raw}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}/doc")
def get_skill_doc(name: str, format: str = "markdown", registry: RegistryClient = Depends(get_registry)):
    if format not in ("markdown", "json"):
        raise HTTPException(status_code=400, detail="format must be 'markdown' or 'json'")
    skill_dir = _skill_dir_or_404(name, registry)
    manifest_path = _manifest_path(skill_dir)
    if not manifest_path:
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
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "name": name,
        "versions": _sorted_versions(info.get("versions", [])),
        "latest": info.get("latest", ""),
        "ids": info.get("ids", {}),
    }


@router.post("/{name}/validate")
def validate_skill(name: str, registry: RegistryClient = Depends(get_registry)):
    skill_dir = _skill_dir_or_404(name, registry)
    errors = validate_full_skill(skill_dir)
    warnings = lint_full_skill(skill_dir)
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "name": name}


@router.post("/{name}/verify")
def verify_skill(name: str, version: str | None = None, registry: RegistryClient = Depends(get_registry)):
    return registry.verify(name, version)


@router.post("/{name}/install", dependencies=[Depends(require_api_key)])
def install_skill(name: str, req: InstallRequest, registry: RegistryClient = Depends(get_registry)):
    # Resolve the install target inside the workspace sandbox. RegistryClient
    # installs into <target_dir>/<name>, so pass the parent directory.
    if req.target:
        target = resolve_in_workspace(req.target)
        parent = target.parent if target.name == name else target
    else:
        # Default to a dedicated subdir so installs never collide with scaffolds.
        parent = resolve_in_workspace("installed")
        parent.mkdir(parents=True, exist_ok=True)
    try:
        installed = registry.install(name, target_dir=parent, version=req.version, verify=req.verify)
    except ValidationError as e:
        audit.record("Skill Install", name, req.version, status="error", details=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    resolved_version = req.version or registry.info(name).get("latest")
    audit.record("Skill Installed", name, resolved_version, details=f"Installed to {installed}")
    return {"success": True, "name": name, "version": resolved_version, "path": str(installed)}


@router.post("/build", dependencies=[Depends(require_api_key)])
def build_skill(req: BuildRequest):
    target = resolve_in_workspace(req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {target}")

    errors = validate_full_skill(target)
    if errors:
        return {"success": False, "errors": errors}

    manifest_path = _manifest_path(target)
    if not manifest_path:
        raise HTTPException(status_code=404, detail="No manifest found")
    manifest = load_manifest(manifest_path)
    skill_id = compute_skill_id(manifest, target)
    return {
        "success": True,
        "name": manifest["name"],
        "version": manifest["version"],
        "id": skill_id,
        "warnings": lint_full_skill(target),
    }


@router.post("/publish", dependencies=[Depends(require_api_key)])
def publish_skill(req: PublishRequest, registry: RegistryClient = Depends(get_registry)):
    target = resolve_in_workspace(req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {target}")
    try:
        result = registry.publish(target, force=req.force)
    except ValidationError as e:
        audit.record("Skill Publish", status="error", details=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    audit.record(
        "Skill Published", result["name"], result["version"],
        details=f"Published with hash {result['id'].split('/')[3][:12]}",
    )
    return {
        "success": True,
        "name": result["name"],
        "version": result["version"],
        "id": result["id"],
        "path": result["path"],
    }


@router.post("/scaffold", dependencies=[Depends(require_api_key)])
def scaffold_skill(req: ScaffoldRequest, registry: RegistryClient = Depends(get_registry)):
    manifest = dict(req.manifest or {})
    name = manifest.get("name")
    if not name or not isinstance(name, str):
        raise HTTPException(status_code=400, detail="manifest.name is required")

    dest = resolve_in_workspace(name)
    if dest.exists() and not req.force:
        raise HTTPException(status_code=400, detail=f"'{name}' already exists in workspace (use force)")

    entry = manifest.get("entry") or "src/main.py"
    manifest["entry"] = entry
    runtime = manifest.get("runtime", "python")

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "tests").mkdir(exist_ok=True)
    entry_path = dest / entry
    entry_path.parent.mkdir(parents=True, exist_ok=True)
    if not entry_path.exists():
        entry_path.write_text(_entry_stub(name, runtime), encoding="utf-8")

    for rel, content in (req.files or {}).items():
        fp = resolve_in_workspace(str(Path(name) / rel))
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    from skill_sdk.validation import _parse_frontmatter, find_manifest_file

    manifest.pop("id", None)
    manifest.pop("body", None)
    body = (req.manifest or {}).get("body", "")

    frontmatter = yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False).strip()
    text = f"---\n{frontmatter}\n---"
    if body:
        text += f"\n\n{body.strip()}\n"
    (dest / "SKILL.md").write_text(text, encoding="utf-8")

    errors = validate_full_skill(dest)
    if errors:
        audit.record("Skill Scaffold", name, manifest.get("version"), status="error",
                     details="; ".join(errors[:3]))
        return {"success": False, "errors": errors, "path": str(dest)}

    audit.record("Skill Scaffolded", name, manifest.get("version"), details=f"Scaffolded at {dest}")

    published = None
    if req.publish:
        try:
            result = registry.publish(dest, force=req.force)
            published = {"id": result["id"], "version": result["version"]}
            audit.record("Skill Published", result["name"], result["version"],
                         details=f"Published with hash {result['id'].split('/')[3][:12]}")
        except ValidationError as e:
            audit.record("Skill Publish", name, manifest.get("version"), status="error", details=str(e))
            return {"success": False, "errors": [str(e)], "path": str(dest), "scaffolded": True}

    return {"success": True, "name": name, "path": str(dest), "published": published}


# -- helpers ----------------------------------------------------------------

def _skill_dir_or_404(name: str, registry: RegistryClient) -> Path:
    try:
        info = registry.info(name)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    rel_path = info.get("locations", {}).get("local")
    if not rel_path:
        raise HTTPException(status_code=404, detail="Skill files not found locally")
    return get_registry_path() / rel_path


def _entry_stub(name: str, runtime: str) -> str:
    if runtime == "typescript":
        return (
            "import type { Skill, SkillContext, SkillEvent, SkillCommand, "
            "SkillResult, HealthStatus } from '@agent-skills/sdk'\n\n"
            "export class GeneratedSkill implements Skill {\n"
            f"  name = '{name}'\n"
            "  version = '0.1.0'\n"
            "  skillId = ''\n"
            "  async initialize(_ctx: SkillContext): Promise<void> {}\n"
            "  async handleEvent(event: SkillEvent): Promise<SkillResult> {\n"
            "    return { status: 'success', data: {}, message: `event ${event.name}` }\n  }\n"
            "  async handleCommand(command: SkillCommand): Promise<SkillResult> {\n"
            "    return { status: 'success', data: {}, message: `command ${command.name}` }\n  }\n"
            "  async healthCheck(): Promise<HealthStatus> {\n"
            "    return { healthy: true, version: this.version, details: {} }\n  }\n"
            "  async shutdown(): Promise<void> {}\n}\n"
        )
    return (
        "from skill_sdk import BaseSkill, SkillContext, SkillEvent, SkillCommand, "
        "SkillResult, HealthStatus\n\n\n"
        "class Skill(BaseSkill):\n"
        f"    name = \"{name}\"\n"
        "    version = \"0.1.0\"\n\n"
        "    async def initialize(self, ctx: SkillContext) -> None:\n"
        "        self.logger = ctx.logger\n\n"
        "    async def handle_event(self, event: SkillEvent) -> SkillResult:\n"
        "        return SkillResult(status=\"success\", message=f\"Received event: {event.name}\")\n\n"
        "    async def handle_command(self, command: SkillCommand) -> SkillResult:\n"
        "        return SkillResult(status=\"success\", message=f\"Executed command: {command.name}\")\n\n"
        "    async def health_check(self) -> HealthStatus:\n"
        "        return HealthStatus(healthy=True, version=self.version)\n\n"
        "    async def shutdown(self) -> None:\n"
        "        pass\n"
    )
