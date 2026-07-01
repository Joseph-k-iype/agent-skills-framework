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


# ---------------------------------------------------------------------------
# Curation endpoint tests (Task 6)
# ---------------------------------------------------------------------------


async def test_list_proposed_admin(http, graph_name):
    """Admin can GET /taxonomy/proposed and get a list (may be empty)."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.get("/api/v1/taxonomy/proposed")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "terms" in body
    assert isinstance(body["terms"], list)


async def test_list_proposed_consumer_forbidden(http, graph_name):
    """Consumer token → 403 on GET /taxonomy/proposed."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.CONSUMER)
    async with http as c:
        resp = await c.get("/api/v1/taxonomy/proposed")

    assert resp.status_code == 403, resp.text


async def test_create_term_admin(http, graph_name):
    """Admin can POST /taxonomy/Capability to create a canonical term."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/Capability",
            json={"key": "test.curation.create", "label": "Test Curation Create"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["key"] == "test.curation.create"
    assert body["status"] == "canonical"


async def test_create_term_consumer_forbidden(http, graph_name):
    """Consumer token → 403 on POST /taxonomy/{label}."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.CONSUMER)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/Capability",
            json={"key": "test.curation.forbidden", "label": "Forbidden"},
        )

    assert resp.status_code == 403, resp.text


async def test_create_term_unknown_label(http, graph_name):
    """Unknown label → 400."""
    from app.db.seed_taxonomy import seed_taxonomy

    await seed_taxonomy(graph_name)

    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/BadLabel",
            json={"key": "x", "label": "x"},
        )

    assert resp.status_code == 400, resp.text


async def test_promote_term(http, graph_name):
    """Admin promotes a proposed term; follow-up read shows it as canonical."""
    from app.repositories.taxonomy_repo import TaxonomyRepository

    repo = TaxonomyRepository()

    # Seed a proposed term directly via the repo
    await repo.upsert_term(
        "Capability", "test.promote.me", "Test Promote Me", None, "proposed", None
    )

    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post("/api/v1/taxonomy/Capability/test.promote.me/promote")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["key"] == "test.promote.me"
    assert body["status"] == "canonical"


async def test_promote_unknown_label(http, graph_name):
    """Promote with unknown label → 400."""
    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post("/api/v1/taxonomy/BadLabel/somekey/promote")

    assert resp.status_code == 400, resp.text


async def test_merge_term(http, graph_name):
    """Merge an alias term into a target; merge returns ok: true."""
    from app.repositories.taxonomy_repo import TaxonomyRepository

    repo = TaxonomyRepository()

    # Create two canonical terms: source (alias) and target
    await repo.upsert_term(
        "Capability", "test.merge.alias", "Merge Alias", None, "canonical", None
    )
    await repo.upsert_term(
        "Capability", "test.merge.target", "Merge Target", None, "canonical", None
    )

    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/Capability/test.merge.alias/merge",
            json={"into_key": "test.merge.target"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}


async def test_merge_missing_target(http, graph_name):
    """Merge into a non-existent target → 400."""
    from app.repositories.taxonomy_repo import TaxonomyRepository

    repo = TaxonomyRepository()

    await repo.upsert_term(
        "Capability", "test.merge.orphan", "Orphan", None, "canonical", None
    )

    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/Capability/test.merge.orphan/merge",
            json={"into_key": "nonexistent.target"},
        )

    assert resp.status_code == 400, resp.text


async def test_merge_unknown_label(http, graph_name):
    """Merge with unknown label → 400."""
    _login(RoleName.ADMIN)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/BadLabel/x/merge",
            json={"into_key": "y"},
        )

    assert resp.status_code == 400, resp.text


async def test_promote_consumer_forbidden(http, graph_name):
    """Consumer token → 403 on promote."""
    _login(RoleName.CONSUMER)
    async with http as c:
        resp = await c.post("/api/v1/taxonomy/Capability/somekey/promote")

    assert resp.status_code == 403, resp.text


async def test_merge_consumer_forbidden(http, graph_name):
    """Consumer token → 403 on merge."""
    _login(RoleName.CONSUMER)
    async with http as c:
        resp = await c.post(
            "/api/v1/taxonomy/Capability/x/merge",
            json={"into_key": "y"},
        )

    assert resp.status_code == 403, resp.text
