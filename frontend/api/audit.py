from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .deps import get_registry_path

try:  # cross-process append safety on POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]


def _audit_path() -> Path:
    return get_registry_path() / ".audit.jsonl"


def record(
    action: str,
    skill: str | None = None,
    version: str | None = None,
    status: str = "success",
    details: str = "",
) -> dict[str, Any]:
    """Append one event to the persistent, append-only audit log."""
    entry = {
        "id": uuid.uuid4().hex,
        "action": action,
        "skillName": skill or "",
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "details": details,
    }
    try:
        path = _audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            if fcntl is not None:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
            finally:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as exc:  # audit logging must never fail the caller's request
        print(f"[audit] failed to record event {entry['id']} ({action}): {exc}")
    return entry


def read(limit: int = 200) -> list[dict[str, Any]]:
    """Return the most recent events, newest first."""
    path = _audit_path()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    entries.reverse()
    return entries[: max(0, limit)]
