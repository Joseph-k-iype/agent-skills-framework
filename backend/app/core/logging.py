"""Structured logging + per-request correlation ids."""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

import structlog

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex
    trace_id_var.set(tid)
    return tid


def current_trace_id() -> str:
    return trace_id_var.get()


def _add_trace_id(_, __, event_dict):
    tid = trace_id_var.get()
    if tid:
        event_dict["trace_id"] = tid
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_trace_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "eakso") -> structlog.BoundLogger:
    return structlog.get_logger(name)
