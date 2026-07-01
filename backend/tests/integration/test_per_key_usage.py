"""Per-key usage attribution: SDK-authed usage records ``api_key_id``,
anonymous/public usage records ``api_key_id IS NULL``."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.models import UsageEvent
from app.services.api_key_service import ApiKeyService
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


async def _publish_listing(db, u: CurrentUser) -> dict:
    cs = ConceptService(db, u)
    await cs.create(
        workspace_id="pk_src",
        folder_path="",
        name="Per Key Skill",
        type="skill",
        description="attribution test",
        runtime=None,
        tags=["data"],
        capabilities=[],
        body="# Per Key\nAttribute me.",
        frontmatter={},
    )
    path = "per-key-skill.md"
    await cs.publish(workspace_id="pk_src", path=path, version="1.0.0")
    mp = MarketplaceService(db, u)
    listings = await mp.list_listings(q=None, type=None)
    return next(x for x in listings if x["source_path"] == path)


async def _latest_usage(db, listing_id: str, kind: str) -> UsageEvent:
    row = await db.scalar(
        select(UsageEvent)
        .where(
            UsageEvent.listing_id == uuid.UUID(listing_id),
            UsageEvent.kind == kind,
        )
        .order_by(UsageEvent.created_at.desc())
    )
    assert row is not None
    return row


async def test_sdk_fetch_records_api_key_id(setup, admin_id):
    async with SessionLocal() as db:
        u = _user(admin_id)
        listing = await _publish_listing(db, u)

        # Create a real API key to attribute the fetch to.
        created = await ApiKeyService(db).create(user_id=admin_id, name="pk-fetch")
        api_key_id = uuid.UUID(created["id"])

        mp = MarketplaceService(db, u)
        await mp.fetch_skill(
            listing_id=listing["id"], user_id=u.id, api_key_id=api_key_id
        )
        await db.commit()

        event = await _latest_usage(db, listing["id"], "fetch")
        assert event.api_key_id == api_key_id


async def test_anonymous_usage_records_null_api_key_id(setup, admin_id):
    async with SessionLocal() as db:
        u = _user(admin_id)
        listing = await _publish_listing(db, u)

        mp = MarketplaceService(db, u)
        # Public/anonymous usage path: no api_key_id threaded through.
        await mp.report_usage(listing_id=listing["id"], user_id=None, kind="apply")
        await db.commit()

        event = await _latest_usage(db, listing["id"], "apply")
        assert event.api_key_id is None
