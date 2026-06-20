from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

ID_URI_SCHEME = "skill"
ID_URI_AUTHORITY = "sha256"

# Manifests are excluded from the source hash so that writing the computed ``id``
# back into a manifest does not change the hash.
MANIFEST_NAMES = frozenset({"skill.yaml", "skill.yml", "skill.json"})

# Directory names that never contribute to a skill's identity. ``tests`` is here
# because identity is the *shippable artifact*; editing a test must not churn the
# skill ID. Any path component beginning with "." (e.g. ``.git``, ``.env`` dirs)
# is also excluded.
EXCLUDED_DIR_NAMES = frozenset({"__pycache__", "node_modules", "dist", "tests"})

# Read files in chunks so large/binary assets don't have to be held in memory.
_CHUNK_SIZE = 1 << 16  # 64 KiB


def _is_test_file(name: str) -> bool:
    if name == "conftest.py":
        return True
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py"):
        return True
    for marker in (".test.", ".spec."):
        if marker in name and name.rsplit(".", 1)[-1] in ("ts", "js", "tsx", "jsx", "mjs", "cjs"):
            return True
    return False


def iter_source_files(skill_root: str | Path) -> Iterator[Path]:
    """Yield every file that contributes to a skill's content hash.

    Excludes manifests, test files/dirs, dotfiles/dotdirs, and build/cache dirs.
    Order is deterministic (sorted by POSIX-relative path) and platform
    independent so the same tree hashes identically on every OS.
    """
    root = Path(skill_root).resolve()
    if not root.exists():
        return
    candidates: list[tuple[str, Path]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        if any(part.startswith(".") or part in EXCLUDED_DIR_NAMES for part in parts):
            continue
        if path.name in MANIFEST_NAMES:
            continue
        if _is_test_file(path.name):
            continue
        candidates.append((rel.as_posix(), path))
    candidates.sort(key=lambda pair: pair[0])
    for _, path in candidates:
        yield path


def compute_skill_id(
    manifest: dict[str, Any],
    skill_root: str | Path,
) -> str:
    hasher = hashlib.sha256()

    # 1) Canonical manifest JSON (the ``id`` field is excluded so stamping the
    #    computed id back in is idempotent). sort_keys recurses into nested objects.
    # ensure_ascii=False so the canonical bytes are the raw UTF-8 of the
    # characters — this lets the TypeScript SDK (whose JSON.stringify never
    # escapes non-ASCII) compute a byte-identical hash.
    manifest_copy = {k: v for k, v in manifest.items() if k != "id"}
    canonical = json.dumps(
        manifest_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    hasher.update(canonical.encode("utf-8"))

    # 2) Each source file: POSIX relative path + NUL + streamed bytes + NUL.
    root = Path(skill_root).resolve()
    for path in iter_source_files(root):
        relative = path.relative_to(root).as_posix()
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\x00")
        try:
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
                    hasher.update(chunk)
        except (OSError, PermissionError):
            continue
        hasher.update(b"\x00")

    digest = hasher.hexdigest()
    name = manifest.get("name", "unknown")
    version = manifest.get("version", "0.0.0")
    return f"{ID_URI_SCHEME}://{ID_URI_AUTHORITY}/{digest}/{name}@{version}"


def validate_skill_id(
    manifest: dict[str, Any],
    skill_root: str | Path,
) -> list[str]:
    errors: list[str] = []
    provided_id = manifest.get("id", "")
    if not provided_id:
        errors.append("Missing 'id' field in manifest")
        return errors

    expected = compute_skill_id(manifest, skill_root)
    if provided_id != expected:
        errors.append(
            f"Skill ID mismatch: expected '{expected}', got '{provided_id}'"
        )
    return errors


def hash_from_skill_id(skill_id: str) -> str:
    parts = skill_id.split("/")
    if len(parts) >= 4 and parts[0].startswith("skill:"):
        return parts[3]
    return ""


def name_version_from_skill_id(skill_id: str) -> tuple[str, str]:
    parts = skill_id.split("/")
    if len(parts) >= 5:
        nv = parts[4]
        if "@" in nv:
            name, version = nv.rsplit("@", 1)
            return name, version
    return "", ""
