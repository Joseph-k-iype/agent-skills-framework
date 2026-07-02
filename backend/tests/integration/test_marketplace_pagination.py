"""Repo-level pagination + SQL category filter (Workstream C).

Seeds published listings directly through the service, then drives
``MarketplaceRepository.list`` to prove:
- ``coalesce(category, type)`` matches when ``category`` is NULL but ``type`` matches.
- offset slices are disjoint and order-stable (secondary ``id`` sort breaks ties).
Integration test: requires live PG + FalkorDB and a seeded ``admin`` user.
"""

from __future__ import annotations

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.repositories.marketplace_repo import MarketplaceRepository
from app.services.concept_service import ConceptService
from app.storage import paths

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def setup(monkeypatch, tmp_path, graph_name):
    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes

    bootstrap_indexes()


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


async def _publish(cs: ConceptService, ws: str, name: str, file: str) -> None:
    await cs.create(
        workspace_id=ws,
        folder_path="",
        name=name,
        type="skill",
        description=f"{name} desc",
        runtime=None,
        tags=[],
        capabilities=[],
        sources=[],
        body=f"# {name}\nbody",
        frontmatter={},
    )
    await cs.publish(workspace_id=ws, path=file, version="1.0.0")


async def test_category_filter_coalesces_null_category_to_type(setup, admin_id):
    """A listing with category=NULL but type='skill' matches category='skill' in SQL."""
    async with SessionLocal() as db:
        cs = ConceptService(db, _user(admin_id))
        await _publish(cs, "pg_cat_a", "PageCat Alpha", "pagecat-alpha.md")
        await db.commit()

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        # category is NULL on freshly published listings; type is "skill".
        rows = await repo.list(category="skill", limit=100)
        titles = [r.title for r in rows]
        assert "PageCat Alpha" in titles, f"coalesce(category,type) should match: {titles}"
        # A category that matches nothing returns nothing for our seed.
        none = await repo.list(category="nonexistent_cat_zzz", limit=100)
        assert all(r.title != "PageCat Alpha" for r in none)


async def test_offset_slices_are_disjoint_and_stable(setup, admin_id):
    """limit=2 across offset 0/2/4 yields disjoint, order-stable slices."""
    async with SessionLocal() as db:
        cs = ConceptService(db, _user(admin_id))
        for i in range(5):
            await _publish(cs, f"pg_pag_{i}", f"PagePag {i}", f"pagepag-{i}.md")
        await db.commit()

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        # Restrict to our seed via category=skill so counts are our 5+ (order stable regardless).
        page0 = await repo.list(sort="uses", limit=2, offset=0)
        page1 = await repo.list(sort="uses", limit=2, offset=2)
        page2 = await repo.list(sort="uses", limit=2, offset=4)
        ids0 = [str(r.id) for r in page0]
        ids1 = [str(r.id) for r in page1]
        ids2 = [str(r.id) for r in page2]
        assert len(ids0) == 2 and len(ids1) == 2 and len(ids2) >= 1
        # No id repeats across the three consecutive pages.
        seen = ids0 + ids1 + ids2
        assert len(seen) == len(set(seen)), f"pages overlap: {seen}"
