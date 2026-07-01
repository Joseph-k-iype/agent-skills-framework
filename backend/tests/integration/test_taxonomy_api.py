"""Integration tests for GET /taxonomy/{capabilities,sources}.

Auth pattern mirrors test_concepts_api.py: dependency-override via
``app.dependency_overrides`` for the happy-path; raw HTTP (no override)
for the 401 case.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import CurrentUser, get_current_user
from app.auth.rbac import RoleName, permissions_for
from app.graph import client
from app.main import app

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


# This file only touches FalkorDB for taxonomy — skip the Postgres cleanup autouse.
@pytest.fixture(autouse=True)
async def _isolate_marketplace_listings():  # noqa: PT004
    yield


@pytest.fixture
def http(monkeypatch, graph_name):
    """ASGI client pointed at the test graph; skips if FalkorDB not available."""
    if not client.ping():
        pytest.skip("FalkorDB not available")
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _login(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="test-user-id", role=role, permissions=permissions_for(role)
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


async def test_capabilities_returns_seeded_terms(http, graph_name):
    """GET /taxonomy/capabilities with skill:read token → 200, correct shape."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.DEVELOPER)
    async with http as c:
        resp = await c.get("/api/v1/taxonomy/capabilities")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "terms" in body

    terms_by_key = {t["key"]: t for t in body["terms"]}

    # extraction must exist with parent_key None
    assert "extraction" in terms_by_key
    assert terms_by_key["extraction"]["parent_key"] is None

    # extraction.table must exist with parent_key "extraction"
    assert "extraction.table" in terms_by_key
    assert terms_by_key["extraction.table"]["parent_key"] == "extraction"

    # All terms have the required fields
    for term in body["terms"]:
        assert "key" in term
        assert "label" in term
        assert "status" in term
        assert "description" in term
        assert "parent_key" in term


async def test_sources_returns_seeded_terms(http, graph_name):
    """GET /taxonomy/sources with skill:read token → 200, includes file and file.csv."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.DEVELOPER)
    async with http as c:
        resp = await c.get("/api/v1/taxonomy/sources")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "terms" in body

    terms_by_key = {t["key"]: t for t in body["terms"]}
    assert "file" in terms_by_key
    assert terms_by_key["file"]["parent_key"] is None
    assert "file.csv" in terms_by_key
    assert terms_by_key["file.csv"]["parent_key"] == "file"


async def test_capabilities_unauthenticated_returns_401(http):
    """No auth header → 401."""
    # No _login call — no override → real auth dependency runs → 401
    async with http as c:
        resp = await c.get("/api/v1/taxonomy/capabilities")

    assert resp.status_code == 401, resp.text


async def test_sources_unauthenticated_returns_401(http):
    """No auth header → 401."""
    async with http as c:
        resp = await c.get("/api/v1/taxonomy/sources")

    assert resp.status_code == 401, resp.text
