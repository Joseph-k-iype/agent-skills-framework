from __future__ import annotations

import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .versioning import SEMVER_PATTERN, max_version

# ``<name>-<version>`` directory layout. Name is kebab-case (non-greedy so the
# greedy SemVer suffix wins), version is a full SemVer (incl. prerelease/build).
_SKILL_DIR_RE = re.compile(
    r"^(?P<name>[a-z][a-z0-9-]*?)-(?P<version>" + SEMVER_PATTERN + r")$"
)


class SkillSource(ABC):
    type: str = ""

    @abstractmethod
    def fetch(self, name: str, version: str, target_dir: Path) -> Path:
        ...

    @abstractmethod
    def list_skills(self) -> dict[str, Any]:
        ...


class LocalSource(SkillSource):
    type = "local"

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    def fetch(self, name: str, version: str, target_dir: Path) -> Path:
        source = self.path / f"{name}-{version}"
        if not source.exists():
            raise FileNotFoundError(f"Skill {name}@{version} not found at {source}")
        dest = target_dir / name
        if dest.exists():
            raise FileExistsError(f"Target {dest} already exists")
        shutil.copytree(
            source, dest,
            ignore=shutil.ignore_patterns("__pycache__", "node_modules", ".git"),
        )
        return dest

    def list_skills(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        skills: dict[str, Any] = {}
        for entry in self.path.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            m = _SKILL_DIR_RE.match(entry.name)
            if m:
                name, version = m.group("name"), m.group("version")
                bucket = skills.setdefault(name, {"versions": [], "latest": ""})
                if version not in bucket["versions"]:
                    bucket["versions"].append(version)
        for bucket in skills.values():
            bucket["latest"] = max_version(bucket["versions"]) or ""
        return skills


class GitSource(SkillSource):
    type = "git"

    def __init__(self, url: str, ref: str = "main", local_cache: str | Path | None = None):
        self.url = url
        self.ref = ref
        self._cache = Path(local_cache) if local_cache else None

    def _ensure_clone(self) -> Path:
        if self._cache and self._cache.exists():
            # Refresh tags so a cached clone doesn't serve a stale skill list.
            try:
                subprocess.run(
                    ["git", "fetch", "--tags", "--force", "--quiet"],
                    cwd=str(self._cache),
                    capture_output=True, text=True, check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            return self._cache
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "repo"
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", self.ref, self.url, str(tmp)],
            capture_output=True, text=True, check=True,
        )
        if self._cache:
            self._cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp), str(self._cache))
            return self._cache
        return tmp

    def fetch(self, name: str, version: str, target_dir: Path) -> Path:
        repo = self._ensure_clone()
        tag = f"skill/{name}/{version}"
        try:
            subprocess.run(
                ["git", "checkout", "tags/" + tag],
                cwd=str(repo),
                capture_output=True, text=True, check=True,
            )
        except subprocess.CalledProcessError:
            raise FileNotFoundError(f"Git tag '{tag}' not found in {self.url}")
        dest = target_dir / name
        if dest.exists():
            raise FileExistsError(f"Target {dest} already exists")

        skill_subdirs = list(repo.glob(f"skills/{name}"))
        if skill_subdirs:
            shutil.copytree(skill_subdirs[0], dest)
        else:
            shutil.copytree(repo, dest,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        return dest

    def list_skills(self) -> dict[str, Any]:
        try:
            repo = self._ensure_clone()
            result = subprocess.run(
                ["git", "tag", "-l", "skill/*/*"],
                cwd=str(repo),
                capture_output=True, text=True, check=True,
            )
            skills: dict[str, Any] = {}
            for tag in result.stdout.strip().splitlines():
                parts = tag.strip().split("/")
                if len(parts) >= 3:
                    name, version = parts[1], parts[2]
                    bucket = skills.setdefault(name, {"versions": [], "latest": ""})
                    if version not in bucket["versions"]:
                        bucket["versions"].append(version)
            for bucket in skills.values():
                bucket["latest"] = max_version(bucket["versions"]) or ""
            return skills
        except Exception:
            return {}


def create_source(config: dict[str, Any]) -> SkillSource:
    stype = config.get("type", "local")
    if stype == "local":
        if "path" not in config:
            raise ValueError("local source requires a 'path'")
        return LocalSource(config["path"])
    elif stype == "git":
        if "url" not in config:
            raise ValueError("git source requires a 'url'")
        return GitSource(
            url=config["url"],
            ref=config.get("ref", "main"),
            local_cache=config.get("cache"),
        )
    raise ValueError(f"Unknown source type: {stype}")
