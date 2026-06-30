"""Integration-test-only fixtures.

Integration tests run against the shared dev Postgres (no per-test rollback),
so any listing a test creates would otherwise persist forever and accumulate
as marketplace pollution (e.g. duplicate "Lineage Tracker" rows from
``test_skill_versioning.py``).

The autouse ``_isolate_marketplace_listings`` fixture below makes every
integration test self-cleaning without per-test teardown code: it snapshots
which ``marketplace_listings`` rows exist before the test, and afterwards
deletes whatever new rows appeared. Rows that already existed before the test
-- including the permanent demo catalog seeded by ``app.db.seed`` -- are left
untouched.

This file intentionally lives under ``tests/integration/`` (not the top-level
``tests/conftest.py``) so it only wraps integration tests, not unit tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import MarketplaceListing, UsageEvent


@pytest.fixture(autouse=True)
async def _isolate_marketplace_listings():
    """Delete any ``marketplace_listings`` row created during the test.

    ``skill_versions`` rows cascade-delete via their
    ``ondelete=CASCADE`` FK to ``marketplace_listings``. ``usage_events.listing_id``
    has NO cascade, so usage events for doomed listings are deleted first.
    """
    async with SessionLocal() as db:
        before_ids = set(
            (await db.scalars(select(MarketplaceListing.id))).all()
        )

    yield

    async with SessionLocal() as db:
        after_ids = set(
            (await db.scalars(select(MarketplaceListing.id))).all()
        )
        new_ids = after_ids - before_ids
        if new_ids:
            await db.execute(
                delete(UsageEvent).where(UsageEvent.listing_id.in_(new_ids))
            )
            await db.execute(
                delete(MarketplaceListing).where(MarketplaceListing.id.in_(new_ids))
            )
            await db.commit()
