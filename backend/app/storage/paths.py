"""Path helpers for git-backed workspace bundles.

A workspace lives at ``<workspaces_root>/<workspace_id>`` as a git repo. All
file operations resolve repo-relative paths through :func:`safe_join`, which
guarantees the result stays inside the bundle (no ``..`` traversal escapes).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import settings

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Lowercase kebab-case slug. ``"My Skill!" -> "my-skill"``."""
    return _NON_SLUG.sub("-", value.strip().lower()).strip("-")


def workspace_root(workspace_id: str) -> Path:
    """Absolute path to a workspace bundle directory (not guaranteed to exist)."""
    return Path(settings.workspaces_root) / workspace_id


def safe_join(root: Path | str, *parts: str) -> Path:
    """Join ``parts`` under ``root``, raising ``ValueError`` on traversal escape.

    Accepts parts that themselves contain ``/`` (e.g. ``"a/b.md"``). The final
    resolved path must remain inside ``root``.
    """
    base = Path(root).resolve()
    candidate = base
    for part in parts:
        candidate = candidate / part
    resolved = candidate.resolve()
    if resolved != base and not resolved.is_relative_to(base):
        raise ValueError(f"Path escapes workspace root: {'/'.join(parts)}")
    return resolved
