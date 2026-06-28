"""Lightweight domain event bus.

For Phases 0–3 the bus writes an audit row synchronously and logs the event;
Celery subscribers (e.g. embedding refresh) attach in Phase 2. Keeping a single
publish() seam means handlers can be added without touching call sites.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.logging import get_logger

log = get_logger("events")

Handler = Callable[[str, dict], Awaitable[None]]
_handlers: list[Handler] = []


def subscribe(handler: Handler) -> None:
    _handlers.append(handler)


async def publish(event_type: str, payload: dict) -> None:
    log.info("event", event_type=event_type, **{k: payload.get(k) for k in ("resource_id", "workspace_id")})
    for handler in _handlers:
        try:
            await handler(event_type, payload)
        except Exception as exc:  # a failing subscriber must not break the request
            log.warning("event_handler_failed", event_type=event_type, error=str(exc))
