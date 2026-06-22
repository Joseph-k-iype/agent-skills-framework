from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sdks" / "python"))

from .routes import skills, registry, dashboard, graph, audit, deployments, evaluation

app = FastAPI(
    title="Agent Skills API",
    version="0.1.0",
    description="API for the Agent Skills Framework — manage, validate, build, publish, and install enterprise agent skills",
)

# Origins are configurable for hosted deployments via SKILLS_CORS_ORIGINS
# (comma-separated). Defaults cover the local Vite dev server on its usual ports
# (5173, and 5174 when 5173 is taken). Credentials are not used (auth is a header
# API key, not a cookie), so we keep allow_credentials off and never need "*".
_env_origins = os.environ.get("SKILLS_CORS_ORIGINS", "")
_allow_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(evaluation.router, prefix="/api/skills", tags=["evaluation"])
app.include_router(registry.router, prefix="/api/registry", tags=["registry"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(deployments.router, prefix="/api/deployments", tags=["deployments"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
