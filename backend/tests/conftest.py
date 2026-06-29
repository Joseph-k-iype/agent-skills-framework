"""Shared pytest fixtures.

Graph tests run against a REAL FalkorDB instance using an isolated graph name,
which is deleted after each test. Cypher is never mocked — the engine behaviour
(paths, cycle detection, vector queries) is exactly what we want to verify.
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.graph import client


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    """Force the offline provider for every test so the suite never makes real LLM
    calls (a developer's .env may carry a live key). Tests that exercise provider
    selection override this with their own monkeypatch inside the test body."""
    monkeypatch.setattr(settings, "llm_provider", "local", raising=False)
    yield


@pytest.fixture
def graph_name(monkeypatch) -> str:
    """Point the graph client at a throwaway graph for the duration of a test."""
    name = "eakso_test"
    monkeypatch.setattr(settings, "falkordb_graph", name, raising=False)
    client.reset_client()
    # ensure a clean slate
    try:
        client.get_db().select_graph(name).delete()
    except Exception:
        pass
    yield name
    try:
        client.get_db().select_graph(name).delete()
    except Exception:
        pass
    client.reset_client()
