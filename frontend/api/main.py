from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sdks" / "python"))

from .routes import skills, registry, dashboard, graph

app = FastAPI(
    title="Agent Skills API",
    version="0.1.0",
    description="API for the Agent Skills Framework — manage, validate, build, publish, and install enterprise agent skills",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(registry.router, prefix="/api/registry", tags=["registry"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
