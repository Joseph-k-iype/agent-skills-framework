from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .hashing import compute_skill_id
from .validation import find_manifest_file, load_manifest, ValidationError
from .versioning import find_repo_root

EXCLUDED_WALK_DIRS = frozenset({".git", "__pycache__", "node_modules", "dist"})


def _find_skill_subtree(worktree: Path, name: str, version: str) -> Path | None:
    """Search a checked-out worktree for the directory holding ``name@version``.

    Tags created before this feature existed don't record a repo-relative path,
    so the only reliable way to locate the skill is to search for a manifest
    whose own ``name``/``version`` match what we're verifying.
    """
    for dirpath, dirnames, _ in os.walk(worktree):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_WALK_DIRS and not d.startswith(".")]
        manifest_path = find_manifest_file(dirpath)
        if manifest_path is None:
            continue
        try:
            manifest = load_manifest(manifest_path)
        except ValidationError:
            continue
        if manifest.get("name") == name and manifest.get("version") == version:
            return Path(dirpath)
    return None


def verify_against_git(registry: Any, name: str, version: str | None = None) -> dict[str, Any]:
    """Cross-check a published skill's content-addressed id against git history.

    Checks out the git tag recorded at publish time into a temporary worktree
    and recomputes the id from that source tree, comparing it against the id
    recorded in the registry index. Returns ``{"valid": None, ...}`` (not a
    failure) when there's nothing to check — e.g. no git tag was ever recorded
    for this version.
    """
    try:
        entry = registry.info(name)
    except ValidationError as e:
        return {"valid": False, "name": name, "errors": [str(e)]}

    check_version = version or entry.get("latest")
    if check_version not in entry.get("versions", []):
        return {"valid": False, "name": name, "errors": [f"Version {check_version} not found"]}

    git_tag = entry.get("git_tags", {}).get(check_version)
    if not git_tag:
        return {
            "valid": None,
            "name": name,
            "version": check_version,
            "reason": "no git tag recorded",
        }

    repo_root = find_repo_root(registry.registry_path)
    if repo_root is None:
        return {
            "valid": None,
            "name": name,
            "version": check_version,
            "reason": "no git repository found",
        }

    expected_id = entry.get("ids", {}).get(check_version)
    tmp_dir = Path(tempfile.mkdtemp(prefix="skill-verify-git-"))
    worktree = tmp_dir / "wt"
    try:
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), git_tag],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {
                "valid": False,
                "name": name,
                "version": check_version,
                "errors": [f"git worktree add failed: {(result.stderr or '').strip()}"],
            }

        skill_dir = _find_skill_subtree(worktree, name, check_version)
        if skill_dir is None:
            return {
                "valid": False,
                "name": name,
                "version": check_version,
                "errors": [f"No manifest for {name}@{check_version} found in tag {git_tag}"],
            }

        manifest_path = find_manifest_file(skill_dir)
        manifest = load_manifest(manifest_path)
        actual_id = compute_skill_id(manifest, skill_dir)

        if actual_id != expected_id:
            return {
                "valid": False,
                "name": name,
                "version": check_version,
                "errors": [f"Hash mismatch: expected {expected_id}, computed {actual_id}"],
            }

        return {
            "valid": True,
            "name": name,
            "version": check_version,
            "id": actual_id,
            "git_tag": git_tag,
        }
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        with contextlib.suppress(OSError):
            shutil.rmtree(tmp_dir, ignore_errors=True)
