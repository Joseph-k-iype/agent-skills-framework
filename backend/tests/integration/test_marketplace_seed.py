"""Demo marketplace seed: idempotency + broadened search.

Verifies ``seed_marketplace_demo`` inserts a varied, real demo catalog exactly
once (safe to run on every app start / ``python -m app.db.seed``), and that
``MarketplaceRepository.list(q=...)`` matches on summary text and on tags, not
just the title (the storefront search should find a skill called "Geocoder"
when searching for a word that only appears in its summary or tags).

These tests rely on ``seed_marketplace_demo`` being idempotent (re-running it
is always a no-op once the demo catalog exists) plus the autouse
``_isolate_marketplace_listings`` fixture in ``conftest.py``, which deletes
only the rows a test newly creates. That means: if the permanent demo catalog
already exists in the dev DB, ``seed_marketplace_demo`` here is a no-op and
nothing is cleaned up at teardown (the demo survives); if it doesn't exist
yet, this test creates it and the autouse fixture removes it afterwards. No
explicit demo cleanup is needed (or wanted) in this file.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.seed_marketplace import DEMO_WORKSPACE_ID, seed_marketplace_demo
from app.db.session import SessionLocal
from app.models import MarketplaceListing
from app.repositories.marketplace_repo import MarketplaceRepository
from app.services.marketplace_service import MarketplaceService

pytestmark = pytest.mark.asyncio


async def test_seed_marketplace_demo_is_idempotent():
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)

    async with SessionLocal() as db:
        rows = (
            await db.scalars(
                select(MarketplaceListing).where(
                    MarketplaceListing.source_workspace_id == DEMO_WORKSPACE_ID
                )
            )
        ).all()
    count_first = len(rows)
    assert count_first >= 10

    # Each demo listing has a v1 SkillVersion with non-empty content, and the
    # listing's latest_sha/latest_version point at it.
    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        for listing in rows:
            assert listing.latest_version == 1
            assert listing.latest_sha
            versions = await repo.list_versions(listing.id)
            assert len(versions) == 1
            v1 = versions[0]
            assert v1.version == 1
            assert v1.content_sha == listing.latest_sha
            assert v1.content and v1.content.strip()

    # Re-running must not duplicate rows.
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)

    async with SessionLocal() as db:
        rows_again = (
            await db.scalars(
                select(MarketplaceListing).where(
                    MarketplaceListing.source_workspace_id == DEMO_WORKSPACE_ID
                )
            )
        ).all()
    assert len(rows_again) == count_first


async def test_search_matches_summary_and_tag_not_just_title():
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        all_demo = (
            await db.scalars(
                select(MarketplaceListing).where(
                    MarketplaceListing.source_workspace_id == DEMO_WORKSPACE_ID
                )
            )
        ).all()

        # Pick a listing and a word from its summary that does NOT appear in
        # its title, to prove the summary is actually searched.
        target = next(
            x
            for x in all_demo
            if x.summary and "geocod" not in x.summary.lower()
            and x.summary.split()
        )
        summary_word = next(
            w.strip(".,()").lower()
            for w in target.summary.split()
            if len(w.strip(".,()")) > 4 and w.strip(".,()").lower() not in target.title.lower()
        )
        by_summary = await repo.list(q=summary_word, limit=200)
        assert any(x.id == target.id for x in by_summary), (
            f"expected listing {target.title!r} to match q={summary_word!r} via summary"
        )

        # Pick a listing+tag where the tag text doesn't appear in the title.
        tag_target = next(x for x in all_demo if x.tags)
        tag = next(
            t for t in tag_target.tags if t.lower() not in tag_target.title.lower()
        )
        by_tag = await repo.list(q=tag, limit=200)
        assert any(x.id == tag_target.id for x in by_tag), (
            f"expected listing {tag_target.title!r} to match q={tag!r} via tags"
        )


async def test_public_get_serves_stored_skill_version_content():
    """Demo listings have no on-disk bundle (only a SkillVersion.content
    snapshot), so the public detail endpoint must fall back to that stored
    content instead of returning an empty README from BundleRepo."""
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)

    async with SessionLocal() as db:
        listing = (
            await db.scalars(
                select(MarketplaceListing).where(
                    MarketplaceListing.source_workspace_id == DEMO_WORKSPACE_ID,
                    MarketplaceListing.title == "Geocoder",
                )
            )
        ).first()
        assert listing is not None

        service = MarketplaceService(db, None)
        out = await service.public_get(str(listing.id))

        assert out["content"], "expected non-empty content for demo listing"
        assert "# Geocoder" in out["content"]
        assert "Resolve addresses and place names to coordinates" in out["content"]
        # is_public gate and versions payload remain intact.
        assert "versions" in out and len(out["versions"]) == 1
        assert out["versions"][0]["version"] == 1
