"""Per-skill stats & clone — repo aggregation + clone service.

Runs against the shared dev Postgres (integration conftest self-cleans any
marketplace_listings rows created here).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.models import MarketplaceListing, UsageEvent
from app.repositories.marketplace_repo import MarketplaceRepository
from app.services.concept_service import ConceptService
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


async def _make_listing(db) -> MarketplaceListing:
    row = MarketplaceListing(
        source_workspace_id=f"stats_{uuid.uuid4().hex[:8]}",
        source_path="x.md",
        version="1.0.0",
        title="Stat Skill",
        summary="s",
        type="skill",
    )
    db.add(row)
    await db.flush()
    return row


async def test_uses_cumulative_offsets_and_ends_at_total():
    async with SessionLocal() as db:
        listing = await _make_listing(db)
        repo = MarketplaceRepository(db)
        now = datetime.now(timezone.utc)
        # 2 apply events BEFORE the 90-day window (100 days ago) → pre-window offset.
        # Then 1 at 10 days ago, 2 at 5 days ago, 1 today (in window).
        offsets = [
            (100, 2),
            (10, 1),
            (5, 2),
            (0, 1),
        ]
        for days_ago, count in offsets:
            for _ in range(count):
                db.add(
                    UsageEvent(
                        listing_id=listing.id,
                        kind="apply",
                        meta={},
                        created_at=now - timedelta(days=days_ago),
                    )
                )
        await db.flush()

        series = await repo.uses_cumulative(listing.id, days=90)
        assert series, "expected a non-empty cumulative series"
        # Every point is a dict with ISO date + int cumulative.
        for pt in series:
            assert set(pt.keys()) == {"date", "cumulative"}
            assert len(pt["date"]) == 10  # YYYY-MM-DD
        # Monotonic non-decreasing.
        cums = [p["cumulative"] for p in series]
        assert cums == sorted(cums)
        # First in-window point already includes the pre-window offset of 2.
        assert cums[0] >= 2
        # Ends at the current total of all apply events (2+1+2+1 = 6).
        assert cums[-1] == 6
        await db.rollback()


async def test_uses_cumulative_empty_returns_list():
    async with SessionLocal() as db:
        listing = await _make_listing(db)
        repo = MarketplaceRepository(db)
        series = await repo.uses_cumulative(listing.id, days=90)
        assert series == []
        await db.rollback()


async def test_increment_clones():
    async with SessionLocal() as db:
        listing = await _make_listing(db)
        repo = MarketplaceRepository(db)
        assert listing.clones == 0
        await repo.increment_clones(listing.id)
        await repo.increment_clones(listing.id)
        await db.refresh(listing)
        assert listing.clones == 2
        await db.rollback()


async def test_clone_to_workspace(setup, admin_id):
    async with SessionLocal() as db:
        u = _user(admin_id)
        cs = ConceptService(db, u)
        await cs.create(
            workspace_id="clone_src",
            folder_path="",
            name="Clonable Skill",
            type="skill",
            description="does things",
            runtime=None,
            tags=["data"],
            capabilities=[],
            body="# Body\nHello.",
            frontmatter={},
        )
        await cs.publish(workspace_id="clone_src", path="clonable-skill.md", version="1.0.0")

        mp = MarketplaceService(db, u)
        listings = await mp.list_listings(q=None, type=None)
        listing = next(x for x in listings if x["source_path"] == "clonable-skill.md")
        lid = listing["id"]

        result = await mp.clone_to_workspace(
            listing_id=lid, workspace_id="clone_dst", folder_path="", name=None, version=None
        )
        assert result["workspace_id"] == "clone_dst"
        assert result["path"].endswith(".md")

        # Concept exists with provenance frontmatter carrying source + clone markers.
        created = cs.get("clone_dst", result["path"])
        assert "Hello." in created.body
        assert created.frontmatter.get("source_listing_id") == lid
        assert created.frontmatter.get("cloned_from") == "Clonable Skill"
        assert created.frontmatter.get("source_sha")
        assert created.frontmatter.get("cloned_at")

        # clones counter bumped + a kind="clone" usage event logged.
        detail = await mp.public_get(lid)
        assert detail["clones"] == 1
        ev = await db.scalar(
            UsageEvent.__table__.select().where(
                (UsageEvent.listing_id == uuid.UUID(lid)) & (UsageEvent.kind == "clone")
            )
        )
        assert ev is not None
        await db.commit()


async def test_clone_missing_listing_raises(setup, admin_id):
    from app.api.errors import NotFoundError

    async with SessionLocal() as db:
        mp = MarketplaceService(db, _user(admin_id))
        with pytest.raises(NotFoundError):
            await mp.clone_to_workspace(
                listing_id=str(uuid.uuid4()),
                workspace_id="clone_dst",
                folder_path="",
                name=None,
                version=None,
            )
