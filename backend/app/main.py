"""EAKSO FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, new_trace_id
from app.graph.indexes import bootstrap_indexes

configure_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Bootstrap graph indexes (idempotent). Tolerate FalkorDB being absent at
    # boot — /readyz reports the real state.
    try:
        bootstrap_indexes()
    except Exception as exc:  # pragma: no cover
        log.warning("graph_bootstrap_skipped", error=str(exc))
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _trace(request: Request, call_next):
        tid = new_trace_id()
        response = await call_next(request)
        response.headers["x-trace-id"] = tid
        return response

    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
