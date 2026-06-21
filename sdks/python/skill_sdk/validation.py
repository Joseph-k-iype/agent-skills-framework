from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .hashing import validate_skill_id

SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "spec" / "skill-schema.json"

SKILL_MD_NAMES = frozenset({"SKILL.md"})
LEGACY_MANIFEST_NAMES = frozenset({"skill.yaml", "skill.yml", "skill.json"})
SKILL_MANIFEST_NAMES = SKILL_MD_NAMES | LEGACY_MANIFEST_NAMES


def find_manifest_file(skill_dir: str | Path) -> Path | None:
    skill_dir = Path(skill_dir).resolve()
    for name in ("SKILL.md", "skill.yaml", "skill.yml", "skill.json"):
        p = skill_dir / name
        if p.exists():
            return p
    return None


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str] | None:
    stripped = text.lstrip("\ufeff").lstrip("\n")
    if not stripped.startswith("---"):
        return None
    stripped = stripped[3:]
    # The closing delimiter must be a line consisting of exactly "---" (a
    # plain substring search for "\n---" would also match an unindented
    # "---" line that happens to appear inside a YAML block-scalar value,
    # e.g. a `description: |-` field whose content includes a markdown
    # horizontal rule \u2014 truncating the manifest silently instead of raising).
    lines = stripped.split("\n")
    end_line = None
    for i, line in enumerate(lines):
        if line.rstrip() == "---":
            end_line = i
            break
    if end_line is None:
        return None
    yaml_block = "\n".join(lines[:end_line])
    body = "\n".join(lines[end_line + 1:]).lstrip("\n")
    try:
        manifest = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return None
    if not isinstance(manifest, dict):
        return None
    return manifest, body


class ValidationError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        self.errors = errors or []
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        if self.errors:
            return self.message + "\n" + "\n".join(f"  - {e}" for e in self.errors)
        return self.message


def _validate_required_fields(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["name", "version", "description", "runtime", "api_version", "entry"]
    for field in required:
        if field not in manifest:
            errors.append(f"Missing required field: '{field}'")
    return errors


def _validate_name(name: Any) -> list[str]:
    if not isinstance(name, str):
        return [f"Invalid name: must be a string, got {type(name).__name__}"]
    errors: list[str] = []
    if not re.match(r"^[a-z][a-z0-9-]*$", name):
        errors.append(f"Invalid name '{name}': must be kebab-case, start with a letter")
    if len(name) < 2:
        errors.append(f"Name '{name}' too short: minimum 2 characters")
    if len(name) > 64:
        errors.append(f"Name '{name}' too long: maximum 64 characters")
    return errors


def _validate_version(version: Any) -> list[str]:
    if not isinstance(version, str):
        return [f"Invalid version: must be a string, got {type(version).__name__}"]
    from .versioning import is_semver

    if not is_semver(version):
        return [f"Invalid version '{version}': must be SemVer (e.g. 1.0.0 or 1.2.3-rc.1)"]
    return []


def _validate_runtime(runtime: Any) -> list[str]:
    if not isinstance(runtime, str):
        return [f"Invalid runtime: must be a string, got {type(runtime).__name__}"]
    errors: list[str] = []
    if runtime not in ("python", "typescript"):
        errors.append(f"Invalid runtime '{runtime}': must be 'python' or 'typescript'")
    return errors


def _validate_api_version(api_version: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(api_version, int):
        errors.append(f"api_version must be an integer, got {type(api_version).__name__}")
    elif api_version < 1:
        errors.append(f"api_version must be >= 1, got {api_version}")
    return errors


def _validate_entry(entry: Any, runtime: str, skill_root: Path | None = None) -> list[str]:
    if not isinstance(entry, str):
        return [f"entry must be a string, got {type(entry).__name__}"]
    errors: list[str] = []
    if runtime == "python" and not entry.endswith(".py"):
        errors.append(f"Python entry point must be a .py file, got '{entry}'")
    if runtime == "typescript" and not entry.endswith((".ts", ".js")):
        errors.append(f"TypeScript entry point must be a .ts or .js file, got '{entry}'")
    if skill_root:
        entry_path = (skill_root / entry).resolve()
        if not entry_path.exists():
            errors.append(f"Entry point '{entry}' not found at {entry_path}")
    return errors


def _validate_commands(commands: Any) -> list[str]:
    if not isinstance(commands, list):
        return [f"commands must be a list, got {type(commands).__name__}"]
    errors: list[str] = []
    for i, cmd in enumerate(commands):
        if not isinstance(cmd, str):
            errors.append(f"Command at index {i} must be a string, got {type(cmd).__name__}")
        elif not cmd.startswith("/"):
            errors.append(f"Command '{cmd}' must start with '/'")
    return errors


def _validate_events(events: Any) -> list[str]:
    if not isinstance(events, list):
        return [f"events must be a list, got {type(events).__name__}"]
    errors: list[str] = []
    for i, ev in enumerate(events):
        if not isinstance(ev, str):
            errors.append(f"Event at index {i} must be a string, got {type(ev).__name__}")
        elif not ev.strip():
            errors.append(f"Event at index {i} cannot be empty")
    return errors


def _validate_triggers(triggers: Any) -> list[str]:
    if not isinstance(triggers, dict):
        return [f"triggers must be a dict, got {type(triggers).__name__}"]
    errors: list[str] = []
    if "events" in triggers:
        errors.extend(_validate_events(triggers["events"]))
    if "commands" in triggers:
        errors.extend(_validate_commands(triggers["commands"]))
    return errors


def _validate_description(description: Any) -> list[str]:
    if description is not None and not isinstance(description, str):
        return [f"description must be a string, got {type(description).__name__}"]
    return []


def _validate_capabilities(capabilities: Any) -> list[str]:
    if not isinstance(capabilities, list):
        return [f"capabilities must be a list, got {type(capabilities).__name__}"]
    errors: list[str] = []
    for i, cap in enumerate(capabilities):
        if not isinstance(cap, str):
            errors.append(f"capability at index {i} must be a string, got {type(cap).__name__}")
        elif not cap.strip():
            errors.append(f"capability at index {i} cannot be empty")
    return errors


def _validate_config(config: Any) -> list[str]:
    if not isinstance(config, dict):
        return [f"config must be a dict, got {type(config).__name__}"]
    errors: list[str] = []
    if "required" in config:
        if not isinstance(config["required"], list):
            errors.append("config.required must be a list")
        else:
            for i, key in enumerate(config["required"]):
                if not isinstance(key, str):
                    errors.append(f"config.required[{i}] must be a string, got {type(key).__name__}")
    if "schema" in config and not isinstance(config["schema"], dict):
        errors.append("config.schema must be a dict")
    return errors


def _validate_dependencies(deps: Any) -> list[str]:
    if not isinstance(deps, dict):
        return [f"dependencies must be a dict, got {type(deps).__name__}"]
    errors: list[str] = []
    allowed = {"pip", "npm", "skills"}
    for key in deps:
        if key not in allowed:
            errors.append(f"Unknown dependency type '{key}'")
        elif not isinstance(deps[key], list):
            errors.append(f"dependencies.{key} must be a list")
        else:
            for i, dep in enumerate(deps[key]):
                if not isinstance(dep, str):
                    errors.append(f"dependencies.{key}[{i}] must be a string, got {type(dep).__name__}")
    return errors


def _validate_skill_dependencies(deps: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    skill_deps = deps.get("skills", [])
    for dep in skill_deps:
        if not isinstance(dep, str):
            errors.append(f"Skill dependency must be a string, got {type(dep).__name__}")
            continue
        if "@" not in dep:
            errors.append(f"Skill dependency '{dep}' must specify version (e.g. data-quality@^1.0.0)")
        else:
            name_part = dep.split("@")[0]
            if not re.match(r"^[a-z][a-z0-9-]*$", name_part):
                errors.append(f"Invalid skill dependency name '{name_part}' in '{dep}'")
    return errors


def _validate_permissions(perms: Any) -> list[str]:
    if not isinstance(perms, list):
        return [f"permissions must be a list, got {type(perms).__name__}"]
    errors: list[str] = []
    valid_actions = {"read", "write", "create", "delete", "list", "execute"}
    for i, perm in enumerate(perms):
        if not isinstance(perm, dict):
            errors.append(f"permissions[{i}] must be a dict, got {type(perm).__name__}")
            continue
        if "resource" not in perm:
            errors.append(f"permissions[{i}]: missing required field 'resource'")
        elif not isinstance(perm["resource"], str):
            errors.append(f"permissions[{i}].resource must be a string")
        if "actions" not in perm:
            errors.append(f"permissions[{i}]: missing required field 'actions'")
        elif not isinstance(perm["actions"], list):
            errors.append(f"permissions[{i}].actions must be a list")
        else:
            for j, action in enumerate(perm["actions"]):
                if not isinstance(action, str):
                    errors.append(f"permissions[{i}].actions[{j}] must be a string")
                elif action not in valid_actions:
                    errors.append(f"permissions[{i}].actions[{j}]: invalid action '{action}'")
    return errors


def _validate_lifecycle(lifecycle: Any) -> list[str]:
    if lifecycle is None:
        return []
    if not isinstance(lifecycle, dict):
        return [f"lifecycle must be a dict, got {type(lifecycle).__name__}"]
    errors: list[str] = []
    valid_hooks = {"on_install", "on_uninstall", "on_upgrade"}
    for key in lifecycle:
        if key not in valid_hooks:
            errors.append(f"Unknown lifecycle hook '{key}'")
        elif not isinstance(lifecycle[key], str):
            errors.append(f"lifecycle.{key} must be a string")
    return errors


def _validate_id(manifest_id: Any) -> list[str]:
    if manifest_id is None:
        return []
    if not isinstance(manifest_id, str):
        return [f"id must be a string, got {type(manifest_id).__name__}"]
    from .versioning import SEMVER_PATTERN

    errors: list[str] = []
    pattern = r"^skill://sha256/[a-f0-9]{64}/[a-z][a-z0-9-]*@" + SEMVER_PATTERN + r"$"
    if not re.match(pattern, manifest_id):
        errors.append(f"Invalid id format: '{manifest_id}'")
    return errors


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_required_fields(manifest))
    errors.extend(_validate_id(manifest.get("id")))
    errors.extend(_validate_description(manifest.get("description")))
    if "name" in manifest:
        errors.extend(_validate_name(manifest["name"]))
    if "version" in manifest:
        errors.extend(_validate_version(manifest["version"]))
    if "runtime" in manifest:
        errors.extend(_validate_runtime(manifest["runtime"]))
    if "api_version" in manifest:
        errors.extend(_validate_api_version(manifest["api_version"]))
    if "entry" in manifest:
        errors.extend(_validate_entry(manifest["entry"], manifest.get("runtime", "")))
    if "triggers" in manifest:
        errors.extend(_validate_triggers(manifest["triggers"]))
    if "capabilities" in manifest:
        errors.extend(_validate_capabilities(manifest["capabilities"]))
    if "config" in manifest:
        errors.extend(_validate_config(manifest["config"]))
    if "dependencies" in manifest:
        errors.extend(_validate_dependencies(manifest["dependencies"]))
        errors.extend(_validate_skill_dependencies(manifest["dependencies"]))
    if "permissions" in manifest:
        errors.extend(_validate_permissions(manifest["permissions"]))
    if "lifecycle" in manifest:
        errors.extend(_validate_lifecycle(manifest["lifecycle"]))
    return errors


def validate_manifest_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return [f"Manifest file not found: {path}"]

    try:
        content = path.read_text(encoding="utf-8")
        if path.name in SKILL_MD_NAMES:
            result = _parse_frontmatter(content)
            if result is None:
                return [f"Invalid SKILL.md: no valid frontmatter found in {path}"]
            manifest = result[0]
        elif path.suffix in (".yaml", ".yml"):
            manifest = yaml.safe_load(content)
        else:
            manifest = json.loads(content)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        return [f"Invalid manifest format: {e}"]

    if not isinstance(manifest, dict):
        return ["Manifest must be a JSON/YAML object"]

    errors = validate_manifest(manifest)

    if "id" in manifest:
        errors.extend(validate_skill_id(manifest, path.parent))

    return errors


def validate_full_skill(skill_path: str | Path) -> list[str]:
    skill_path = Path(skill_path).resolve()
    errors: list[str] = []

    manifest_path = find_manifest_file(skill_path)
    if manifest_path is None:
        return [f"No SKILL.md, skill.yaml, or skill.json found in {skill_path}"]

    errors.extend(validate_manifest_file(manifest_path))

    manifest = _load_manifest_raw(manifest_path)
    if manifest:
        entry = manifest.get("entry", "")
        if entry:
            entry_path = (skill_path / entry).resolve()
            if not entry_path.exists():
                errors.append(f"Entry point '{entry}' not found at {entry_path}")

    return errors


def lint_full_skill(skill_path: str | Path) -> list[str]:
    """Non-fatal recommendations (e.g. a missing ``tests/`` dir).

    Kept separate from :func:`validate_full_skill` so advisory notes never block
    ``build``/``publish`` the way a hard validation error does.
    """
    skill_path = Path(skill_path).resolve()
    warnings: list[str] = []
    if not (skill_path / "tests").exists():
        warnings.append("No 'tests/' directory found (recommended)")
    return warnings


def _load_manifest_raw(path: Path) -> dict[str, Any] | None:
    try:
        content = path.read_text(encoding="utf-8")
        if path.name in SKILL_MD_NAMES:
            result = _parse_frontmatter(content)
            if result is not None:
                return result[0]
            return None
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        return json.loads(content)
    except Exception:
        return None


def _dep_names(skill_deps: Any) -> list[str]:
    names: list[str] = []
    for dep in skill_deps or []:
        if isinstance(dep, str):
            names.append(dep.split("@")[0])
    return names


def detect_dependency_cycles(manifest: dict[str, Any], registry_client: Any = None) -> list[str]:
    """Detect cycles in the inter-skill dependency graph.

    The graph is resolved transitively: the root's declared dependencies come
    from ``manifest``; every other node's dependencies are resolved through
    ``registry_client.get_skill_dependencies(name)`` when a client is supplied.
    Without a client only the root's own edges are known, so just self-loops are
    detectable — published peers are required to see cross-skill cycles.
    """
    errors: list[str] = []
    root = manifest.get("name", "")
    root_deps = _dep_names(manifest.get("dependencies", {}).get("skills", []))

    def deps_of(node: str) -> list[str]:
        if node == root:
            return root_deps
        if registry_client is None:
            return []
        try:
            return list(registry_client.get_skill_dependencies(node))
        except Exception:
            return []

    visited: set[str] = set()
    in_stack: set[str] = set()
    reported: set[tuple[str, str]] = set()

    def _dfs(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for neighbor in deps_of(node):
            if neighbor in in_stack:
                key = (node, neighbor)
                if key not in reported:
                    reported.add(key)
                    errors.append(
                        f"Circular dependency detected: '{node}' -> '{neighbor}'"
                    )
                return True
            if neighbor not in visited:
                if _dfs(neighbor):
                    return True
        in_stack.discard(node)
        return False

    _dfs(root)
    return errors


def find_downstream_skills(name: str, registry_client: Any) -> list[str]:
    """Transitive list of skills that depend on ``name``, directly or indirectly.

    Built from a reverse adjacency map over the registry's declared skill
    dependencies — the same data ``detect_dependency_cycles`` walks forward,
    traversed backward here to answer "what breaks if I change this skill?"
    """
    reverse_deps: dict[str, list[str]] = {}
    for skill_name in registry_client.list_skills():
        for dep in registry_client.get_skill_dependencies(skill_name):
            reverse_deps.setdefault(dep, []).append(skill_name)

    downstream: list[str] = []
    seen: set[str] = {name}
    queue = list(reverse_deps.get(name, []))
    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.add(node)
        downstream.append(node)
        queue.extend(reverse_deps.get(node, []))
    return downstream


def validate_manifest_with_path(manifest: dict[str, Any], skill_root: str | Path) -> list[str]:
    errors = validate_manifest(manifest)
    errors.extend(validate_skill_id(manifest, skill_root))
    errors.extend(detect_dependency_cycles(manifest))
    # ``validate_manifest`` calls ``_validate_entry`` without a ``skill_root``,
    # so it only checks the entry's extension, never that the file actually
    # exists. Since this function *does* have the skill root, also check
    # existence here — otherwise a manifest with a nonexistent ``entry`` (e.g.
    # a typo) passes cleanly and `RegistryClient.publish()`/`verify()` can
    # succeed for a skill whose entry point is missing.
    if "entry" in manifest:
        errors.extend(
            _validate_entry(manifest["entry"], manifest.get("runtime", ""), Path(skill_root))
        )
    return errors


def load_manifest(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ValidationError(f"Manifest not found: {path}")

    raw = path.read_text(encoding="utf-8")

    if path.name in SKILL_MD_NAMES:
        result = _parse_frontmatter(raw)
        if result is None:
            raise ValidationError(f"Invalid SKILL.md: no valid frontmatter found in {path}")
        manifest = result[0]
    elif path.suffix in (".yaml", ".yml"):
        try:
            manifest = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
    else:
        try:
            manifest = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

    if not isinstance(manifest, dict):
        raise ValidationError("Manifest must be a JSON/YAML object")

    errors = validate_manifest(manifest)
    if errors:
        raise ValidationError("Manifest validation failed", errors=errors)

    return manifest


def load_manifest_with_body(path: str | Path) -> tuple[dict[str, Any], str]:
    path = Path(path)
    if not path.exists():
        raise ValidationError(f"Manifest not found: {path}")

    raw = path.read_text(encoding="utf-8")

    if path.name in SKILL_MD_NAMES:
        result = _parse_frontmatter(raw)
        if result is None:
            raise ValidationError(f"Invalid SKILL.md: no valid frontmatter found in {path}")
        manifest, body = result
    elif path.suffix in (".yaml", ".yml"):
        try:
            manifest = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
        body = ""
    else:
        try:
            manifest = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        body = ""

    if not isinstance(manifest, dict):
        raise ValidationError("Manifest must be a JSON/YAML object")

    errors = validate_manifest(manifest)
    if errors:
        raise ValidationError("Manifest validation failed", errors=errors)

    return manifest, body
