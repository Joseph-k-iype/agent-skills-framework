from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator

import yaml

from .hashing import compute_skill_id
from .validation import (
    load_manifest,
    ValidationError,
    validate_manifest_with_path,
    detect_dependency_cycles,
    _dep_names,
)
from .versioning import git_tag_skill, git_tag_exists, max_version
from .sources import create_source

try:  # POSIX file locking for cross-process safety; degrades gracefully elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

# Files/dirs that must never be copied into the registry. Mirrors the hashing
# exclusions and, critically, drops dotfiles such as ``.env`` so secrets and
# local caches don't leak into a published, shareable artifact.
COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__", "node_modules", ".git", "dist", ".*", "*.egg-info"
)


def _empty_index() -> dict[str, Any]:
    return {"schema_version": 1, "sources": [], "skills": {}}


class RegistryClient:
    def __init__(self, registry_path: str | Path, auto_tag: bool = True):
        self.registry_path = Path(registry_path).resolve()
        self.index_path = self.registry_path / "index.yaml"
        self.auto_tag = auto_tag
        self._repo_root: Path | None = None

    # -- low level ----------------------------------------------------------

    def _find_repo_root(self, start: Path) -> Path | None:
        for parent in [start] + list(start.parents):
            if (parent / ".git").exists():
                return parent
        return None

    def _ensure_registry(self):
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.registry_path.joinpath("skills").mkdir(exist_ok=True)

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        """Serialize read-modify-write of the index across processes.

        Without an exclusive lock, two concurrent ``publish``/``sync`` calls race
        on the load → mutate → save sequence and silently drop one writer's
        changes (lost update) or interleave a half-written file.
        """
        self._ensure_registry()
        if fcntl is None:  # pragma: no cover - non-POSIX best effort
            yield
            return
        lock_path = self.registry_path / ".index.lock"
        with open(lock_path, "w") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return _empty_index()
        raw = self.index_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            return _empty_index()
        data.setdefault("schema_version", 1)
        data.setdefault("sources", [])
        data.setdefault("skills", {})
        return data

    def _save_index(self, index: dict[str, Any]):
        """Atomically replace the index so a crash mid-write can't corrupt it."""
        self._ensure_registry()
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.registry_path), prefix=".index.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.dump(index, f, default_flow_style=False, sort_keys=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, self.index_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise

    def _manifest_path(self, skill_dir: Path) -> Path | None:
        for name in ("skill.yaml", "skill.yml", "skill.json"):
            candidate = skill_dir / name
            if candidate.exists():
                return candidate
        return None

    def _write_manifest(self, manifest_path: Path, manifest: dict[str, Any]):
        if manifest_path.suffix in (".yaml", ".yml"):
            manifest_path.write_text(
                yaml.dump(manifest, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
        else:
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=False) + "\n",
                encoding="utf-8",
            )

    # -- publish ------------------------------------------------------------

    def publish(
        self,
        skill_path: str | Path,
        force: bool = False,
        tag: bool | None = None,
    ) -> dict[str, Any]:
        skill_path = Path(skill_path).resolve()
        manifest_path = self._manifest_path(skill_path)
        if manifest_path is None:
            raise ValidationError(f"No skill manifest found in {skill_path}")

        # Structural validation + hash are computed from the (read-only) source.
        manifest = load_manifest(manifest_path)
        name = manifest["name"]
        version = manifest["version"]

        skill_id = compute_skill_id(manifest, skill_path)
        stamped = {**manifest, "id": skill_id}

        errors = validate_manifest_with_path(stamped, skill_path)
        if errors:
            raise ValidationError("Skill validation failed", errors=errors)
        cycle_errors = detect_dependency_cycles(stamped, self)
        if cycle_errors:
            raise ValidationError("Dependency cycle detected", errors=cycle_errors)

        dest = self.registry_path / "skills" / f"{name}-{version}"
        do_tag = self.auto_tag if tag is None else tag
        git_tag = None

        with self._locked():
            index = self._load_index()

            if dest.exists():
                if force:
                    shutil.rmtree(dest)
                else:
                    raise ValidationError(
                        f"Skill {name}@{version} already published (use --force to overwrite)"
                    )

            # Non-destructive: copy the source tree, then stamp the computed id
            # into the *registry's* manifest only — the user's working tree is
            # never modified.
            shutil.copytree(skill_path, dest, ignore=COPY_IGNORE)
            dest_manifest = self._manifest_path(dest)
            if dest_manifest is None:  # pragma: no cover - copytree guarantees it
                raise ValidationError("Manifest disappeared during copy")
            self._write_manifest(dest_manifest, stamped)

            if do_tag:
                repo_root = self._find_repo_root(skill_path)
                if repo_root and not git_tag_exists(name, version, repo_root):
                    try:
                        git_tag_skill(name, version, skill_id, repo_root)
                        git_tag = f"skill/{name}/{version}"
                    except (ValidationError, FileNotFoundError):
                        git_tag = None

            self._register_in_index(index, name, version, dest, skill_id, git_tag)
            self._save_index(index)

        return {
            "name": name,
            "version": version,
            "id": skill_id,
            "path": str(dest),
            "git_tag": git_tag,
        }

    def _register_in_index(
        self,
        index: dict[str, Any],
        name: str,
        version: str,
        path: Path,
        skill_id: str,
        git_tag: str | None = None,
    ):
        skills = index.setdefault("skills", {})
        if name not in skills:
            skills[name] = {"versions": [], "latest": version, "ids": {}, "locations": {}}
        entry = skills[name]
        entry.setdefault("versions", [])
        entry.setdefault("ids", {})
        entry.setdefault("locations", {})
        if version not in entry["versions"]:
            entry["versions"].append(version)
        # ``latest`` is the highest SemVer, not the most recently published.
        entry["latest"] = max_version(entry["versions"]) or version
        entry["ids"][version] = skill_id
        entry["locations"]["local"] = str(path.relative_to(self.registry_path))
        if git_tag:
            entry.setdefault("git_tags", {})[version] = git_tag

    # -- read ---------------------------------------------------------------

    def get_skill_dependencies(self, name: str) -> list[str]:
        """Direct skill-dependency *names* of a published skill (latest version).

        Used by cycle detection to walk the graph across the registry.
        """
        index = self._load_index()
        entry = index.get("skills", {}).get(name)
        if not entry:
            return []
        rel = entry.get("locations", {}).get("local")
        if not rel:
            return []
        skill_dir = (self.registry_path / rel).resolve()
        manifest_path = self._manifest_path(skill_dir)
        if manifest_path is None:
            return []
        try:
            manifest = load_manifest(manifest_path)
        except ValidationError:
            return []
        return _dep_names(manifest.get("dependencies", {}).get("skills", []))

    def list_skills(self) -> dict[str, Any]:
        index = self._load_index()
        result = {}
        for name, info in index.get("skills", {}).items():
            result[name] = {
                "latest": info.get("latest", ""),
                "versions": info.get("versions", []),
                "ids": info.get("ids", {}),
            }
        return result

    def info(self, name: str) -> dict[str, Any]:
        index = self._load_index()
        if name not in index.get("skills", {}):
            raise ValidationError(f"Skill '{name}' not found in registry")
        return index["skills"][name]

    # -- install ------------------------------------------------------------

    def install(
        self,
        name: str,
        target_dir: str | Path | None = None,
        version: str | None = None,
        source: str | None = None,
        verify: bool = True,
    ) -> Path:
        index = self._load_index()
        if name not in index.get("skills", {}):
            raise ValidationError(f"Skill '{name}' not found in registry")

        entry = index["skills"][name]
        install_version = version or entry["latest"]
        if version and version not in entry.get("versions", []):
            raise ValidationError(
                f"Skill '{name}' version {version} not found "
                f"(available: {', '.join(entry.get('versions', []))})"
            )

        if source:
            sources_config = [s for s in index.get("sources", []) if s.get("type") == source]
            if sources_config:
                src = create_source(sources_config[0])
                if target_dir is None:
                    target_dir = Path.cwd()
                return src.fetch(name, install_version, Path(target_dir))

        rel_path = entry.get("locations", {}).get("local")
        if not rel_path:
            raise ValidationError(f"No local files for skill '{name}'")

        source_path = (self.registry_path / rel_path).resolve()
        if not source_path.exists():
            raise ValidationError(f"Skill files not found at {source_path}")

        if target_dir is None:
            target_dir = Path.cwd()
        target = Path(target_dir) / name
        if target.exists():
            raise ValidationError(f"Target directory {target} already exists")

        shutil.copytree(source_path, target, ignore=COPY_IGNORE)

        if verify:
            expected_id = entry.get("ids", {}).get(install_version)
            if expected_id:
                manifest_path = self._manifest_path(target)
                manifest = load_manifest(manifest_path) if manifest_path else None
                actual_id = compute_skill_id(manifest, target) if manifest else None
                if actual_id != expected_id:
                    shutil.rmtree(target, ignore_errors=True)
                    raise ValidationError(
                        f"Integrity check failed for {name}@{install_version}: "
                        f"expected {expected_id}, computed {actual_id}"
                    )
        return target

    # -- verify -------------------------------------------------------------

    def verify(self, name: str, version: str | None = None) -> dict[str, Any]:
        index = self._load_index()
        if name not in index.get("skills", {}):
            return {"valid": False, "errors": [f"Skill '{name}' not found in registry"]}

        entry = index["skills"][name]
        check_version = version or entry["latest"]
        if check_version not in entry.get("versions", []):
            return {"valid": False, "errors": [f"Version {check_version} not found"]}

        rel_path = entry.get("locations", {}).get("local")
        if not rel_path:
            return {"valid": False, "errors": ["No local files"]}

        source_path = (self.registry_path / rel_path).resolve()
        if not source_path.exists():
            return {"valid": False, "errors": ["Files not found"]}

        manifest_path = self._manifest_path(source_path)
        if manifest_path is None:
            return {"valid": False, "errors": ["Manifest missing in stored skill"]}

        errors = validate_manifest_with_path(load_manifest(manifest_path), source_path)
        if errors:
            return {"valid": False, "errors": errors}

        return {
            "valid": True,
            "name": name,
            "version": check_version,
            "id": entry.get("ids", {}).get(check_version, ""),
        }

    # -- sources ------------------------------------------------------------

    def add_source(self, source_config: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            index = self._load_index()
            if source_config not in index["sources"]:
                index["sources"].append(source_config)
                self._save_index(index)
        return {"status": "added", "source": source_config}

    def sync_from_sources(self) -> dict[str, Any]:
        with self._locked():
            index = self._load_index()
            synced: list[str] = []
            errors: list[str] = []
            for source_config in index.get("sources", []):
                try:
                    src = create_source(source_config)
                    skills = src.list_skills()
                except Exception as e:
                    errors.append(f"{source_config.get('type', 'unknown')}: {e}")
                    continue
                for name, sinfo in skills.items():
                    entry = index["skills"].setdefault(
                        name, {"versions": [], "latest": "", "ids": {}, "locations": {}}
                    )
                    for ver in sinfo.get("versions", []):
                        if ver not in entry["versions"]:
                            entry["versions"].append(ver)
                    # SemVer-correct latest (string compare made "0.10.0" < "0.9.0").
                    entry["latest"] = max_version(entry["versions"]) or entry.get("latest", "")
                    synced.append(name)
            self._save_index(index)
        return {"synced": len(synced), "skills": synced, "errors": errors}
