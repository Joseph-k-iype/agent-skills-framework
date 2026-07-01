"""Integration tests for concept USES/DERIVED_FROM taxonomy edges (curated-open).

Curated-open rule: indexing a concept with an unknown capability or source must
NEVER raise or return a 4xx.  The unknown term is auto-created as 'proposed'
and the edge is built.  A canonical term's status is NEVER downgraded.
"""

from __future__ import annotations

import uuid

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.repositories.taxonomy_repo import TaxonomyRepository
from app.schemas.concept import ConceptCreate

pytestmark = pytest.mark.asyncio

WS = "test_refs_" + uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Fixtures (mirror test_concept_service.py)
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def setup(monkeypatch, tmp_path, graph_name):
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


# ---------------------------------------------------------------------------
# Helper: query the outgoing USES / DERIVED_FROM neighbours for a concept
# ---------------------------------------------------------------------------


async def _graph_neighbors(workspace_id: str, path: str) -> dict:
    """Return {'capabilities': [...keys], 'sources': [...keys]} for the concept."""
    key = f"{workspace_id}::{path}"
    rows = client.ro_query(
        """
        MATCH (c:Concept {key: $key})
        OPTIONAL MATCH (c)-[:USES]->(cap:Capability)
        OPTIONAL MATCH (c)-[:DERIVED_FROM]->(src:Source)
        RETURN collect(DISTINCT cap.key) AS caps, collect(DISTINCT src.key) AS srcs
        """,
        {"key": key},
    ).result_set or []
    if not rows:
        return {"capabilities": [], "sources": []}
    caps = [k for k in (rows[0][0] or []) if k]
    srcs = [k for k in (rows[0][1] or []) if k]
    return {"capabilities": caps, "sources": srcs}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_unknown_capability_is_proposed_not_rejected(setup, admin_id):
    """Indexing with a totally unknown capability must succeed; term becomes proposed."""
    from app.services.concept_service import ConceptService

    ws = "ws_refs_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        c = await svc.create(
            workspace_id=ws,
            folder_path="",
            name="Edge Concept",
            type="skill",
            description=None,
            runtime=None,
            tags=[],
            capabilities=["totally.new.cap"],
            sources=["file.csv"],
            body="x",
            frontmatter={},
        )

    repo = TaxonomyRepository()
    term = await repo.get_term("Capability", "totally.new.cap")
    assert term is not None, "unknown capability should have been auto-created"
    assert term["status"] == "proposed"

    nbr = await _graph_neighbors(ws, c.path)
    assert "totally.new.cap" in nbr["capabilities"]
    assert "file.csv" in nbr["sources"]


async def test_canonical_term_not_downgraded(setup, admin_id):
    """A canonical term (e.g. 'extraction') must keep status='canonical' after indexing."""
    from app.services.concept_service import ConceptService

    ws = "ws_refs2_" + uuid.uuid4().hex[:8]
    # Seed 'extraction' as canonical first
    repo = TaxonomyRepository()
    await repo.upsert_term("Capability", "extraction", "Extraction", None, "canonical", None)

    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        await svc.create(
            workspace_id=ws,
            folder_path="",
            name="Canonical Test",
            type="skill",
            description=None,
            runtime=None,
            tags=[],
            capabilities=["extraction"],
            sources=[],
            body="y",
            frontmatter={},
        )

    term = await repo.get_term("Capability", "extraction")
    assert term is not None
    assert term["status"] == "canonical", "curated-open must never downgrade a canonical term"

    nbr = await _graph_neighbors(ws, "canonical-test.md")
    assert "extraction" in nbr["capabilities"]


async def test_unknown_source_is_proposed(setup, admin_id):
    """Indexing with an unknown source must create it as proposed."""
    from app.services.concept_service import ConceptService

    ws = "ws_refs3_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        c = await svc.create(
            workspace_id=ws,
            folder_path="",
            name="Source Test",
            type="skill",
            description=None,
            runtime=None,
            tags=[],
            capabilities=[],
            sources=["totally.weird.src"],
            body="z",
            frontmatter={},
        )

    repo = TaxonomyRepository()
    term = await repo.get_term("Source", "totally.weird.src")
    assert term is not None, "unknown source should have been auto-created"
    assert term["status"] == "proposed"

    nbr = await _graph_neighbors(ws, c.path)
    assert "totally.weird.src" in nbr["sources"]


async def test_reindex_clears_and_rebuilds_edges(setup, admin_id):
    """After updating capabilities/sources, old taxonomy edges are removed and new ones added."""
    from app.services.concept_service import ConceptService

    ws = "ws_refs4_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        c = await svc.create(
            workspace_id=ws,
            folder_path="",
            name="Rebuild Test",
            type="skill",
            description=None,
            runtime=None,
            tags=[],
            capabilities=["old.cap"],
            sources=["old.src"],
            body="v1",
            frontmatter={},
        )
        # Update to use different capabilities/sources
        await svc.update(
            workspace_id=ws,
            path=c.path,
            capabilities=["new.cap"],
            sources=["new.src"],
        )

    nbr = await _graph_neighbors(ws, c.path)
    assert "new.cap" in nbr["capabilities"]
    assert "new.src" in nbr["sources"]
    assert "old.cap" not in nbr["capabilities"], "stale USES edge should have been cleared"
    assert "old.src" not in nbr["sources"], "stale DERIVED_FROM edge should have been cleared"
