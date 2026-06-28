"""Standard API response envelope (PRD §06)."""

from __future__ import annotations

from typing import Any

from app.core.logging import current_trace_id


def success(data: Any = None, meta: dict | None = None) -> dict:
    return {"success": True, "data": data, "meta": meta or {}, "errors": []}


def error(code: str, message: str, details: Any = None) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "trace_id": current_trace_id(),
        },
    }
