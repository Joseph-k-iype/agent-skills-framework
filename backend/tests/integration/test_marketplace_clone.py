"""Clone + history endpoints through the real app (httpx ASGI, real PG + FalkorDB)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import CurrentUser, get_current_user
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.main import app
from app.services.concept_service import ConceptService

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def http(monkeypatch, tmp_path, graph_name):
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes

    bootstrap_indexes()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _login(role: str, user_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id, role=role, permissions=permissions_for(role)
    )


async def _seed_listing(admin_id: str) -> str:
    async with SessionLocal() as db:
        u = CurrentUser(
            id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
        )
        cs = ConceptService(db, u)
        await cs.create(
            workspace_id="clone_ep_src",
            folder_path="",
            name="Endpoint Clone Skill",
            type="skill",
            description="d",
            runtime=None,
            tags=["data"],
            capabilities=[],
            body="# Body\nClone me.",
            frontmatter={},
        )
        await cs.publish(workspace_id="clone_ep_src", path="endpoint-clone-skill.md", version="1.0.0")
        from app.services.marketplace_service import MarketplaceService

        mp = MarketplaceService(db, u)
        listings = await mp.list_listings(q=None, type=None)
        lid = next(x for x in listings if x["source_path"] == "endpoint-clone-skill.md")["id"]
        await db.commit()
        return lid


async def test_clone_requires_auth(http, admin_id):
    lid = await _seed_listing(admin_id)
    # no override → real get_current_user → 401
    resp = await http.post(
        f"/api/v1/marketplace/{lid}/clone", json={"workspace_id": "clone_ep_dst"}
    )
    assert resp.status_code == 401


async def test_consumer_forbidden(http, admin_id):
    lid = await _seed_listing(admin_id)
    _login(RoleName.CONSUMER, admin_id)
    resp = await http.post(
        f"/api/v1/marketplace/{lid}/clone", json={"workspace_id": "clone_ep_dst"}
    )
    assert resp.status_code == 403


async def test_clone_ok(http, admin_id):
    lid = await _seed_listing(admin_id)
    _login(RoleName.DEVELOPER, admin_id)
    resp = await http.post(
        f"/api/v1/marketplace/{lid}/clone", json={"workspace_id": "clone_ep_dst"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["workspace_id"] == "clone_ep_dst"
    assert data["path"].endswith(".md")


async def test_public_history(http, admin_id):
    lid = await _seed_listing(admin_id)
    # report an apply so there's at least one usage event
    async with SessionLocal() as db:
        from app.services.marketplace_service import MarketplaceService

        u = CurrentUser(
            id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
        )
        await MarketplaceService(db, u).report_usage(listing_id=lid, user_id=admin_id, kind="apply")
        await db.commit()

    resp = await http.get(f"/api/v1/public/marketplace/{lid}/history?days=90")
    assert resp.status_code == 200
    series = resp.json()["data"]
    assert isinstance(series, list)
    assert series
    assert set(series[-1].keys()) == {"date", "cumulative"}
