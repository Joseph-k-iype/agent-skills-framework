"""Marketplace publish→list→install and insight analytics aggregation."""

from __future__ import annotations

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.services.analytics_service import AnalyticsService
from app.services.concept_service import ConceptService
from app.services.eval_history import record_eval_run
from app.services.marketplace_service import MarketplaceService
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


async def test_publish_lists_then_fetch_and_report_usage(setup, admin_id):
    async with SessionLocal() as db:
        u = _user(admin_id)
        cs = ConceptService(db, u)
        await cs.create(
            workspace_id="mp_src",
            folder_path="",
            name="Lineage Tracker",
            type="skill",
            description="tracks lineage",
            runtime=None,
            tags=["data"],
            capabilities=[],
            body="# Lineage\nTrack origins.",
            frontmatter={},
        )
        path = "lineage-tracker.md"
        await cs.publish(workspace_id="mp_src", path=path, version="1.0.0")

        mp = MarketplaceService(db, u)
        listings = await mp.list_listings(q=None, type=None)
        listing = next(x for x in listings if x["source_path"] == path)
        assert listing["title"] == "Lineage Tracker"
        assert listing["type"] == "skill"

        # SDK consumption: fetch the skill content + a ready system prompt.
        fetched = await mp.fetch_skill(listing_id=listing["id"], user_id=u.id)
        assert "Track origins." in fetched["content"]
        assert fetched["title"] == "Lineage Tracker"
        assert "# Skill: Lineage Tracker" in fetched["system_prompt"]

        # Report an apply-usage → bumps the "uses" counter.
        await mp.report_usage(listing_id=listing["id"], user_id=u.id, kind="apply")
        detail = await mp.get_listing(listing["id"])
        assert detail["downloads"] >= 1
        assert detail["content"]
        await db.commit()


async def test_eval_run_persisted_and_surfaced_in_analytics(setup, admin_id):
    await record_eval_run(
        workspace_id="an_ws",
        concept_path="x.md",
        kind="deep",
        score=3.5,
        summary="improves",
        actor_id=admin_id,
    )
    async with SessionLocal() as db:
        overview = await AnalyticsService(db).overview(workspace_id="an_ws")
        by_kind = {r["kind"]: r for r in overview["eval_summary"]}
        assert "deep" in by_kind
        assert by_kind["deep"]["runs"] >= 1
        assert overview["graph"] is not None  # graph analytics block present
