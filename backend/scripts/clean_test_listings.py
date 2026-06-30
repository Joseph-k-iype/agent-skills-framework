"""Delete marketplace listings left behind by integration tests.

The publish-flow integration tests (e.g. ``test_skill_versioning.py``) create
a listing in a fresh, randomly-named workspace (``ws_xxxxxxxx``) on every
run, against the *shared dev DB*, with no rollback — so rows accumulate over
time (this is how the dev DB ended up with 18 duplicate "Lineage Tracker"
listings). A handful of older fixtures also used the literal workspace id
``mp_src``.

This script removes both: any listing whose ``source_workspace_id`` matches
the ``ws_%`` test convention, or equals ``mp_src``. Their ``skill_versions``
rows cascade-delete via the ``ondelete=CASCADE`` FK
(``skill_versions.listing_id`` -> ``marketplace_listings.id``). The
``usage_events.listing_id`` FK has no cascade, so any usage events recorded
against a doomed listing are deleted explicitly first, in the same
transaction.

Demo listings (``source_workspace_id == 'demo'``, see
``app/db/seed_marketplace.py``) and any real, non-test publish are untouched.

Usage::

    uv run --python 3.12 python scripts/clean_test_listings.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as a plain script (``python scripts/clean_test_listings.py``)
# as well as a module. Direct script execution puts the script's own
# directory on sys.path, not the backend project root, so ``import app``
# would otherwise fail outside of ``python -m``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, or_, select  # noqa: E402

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import MarketplaceListing, UsageEvent  # noqa: E402

log = get_logger("clean_test_listings")

# Matches the literal prefix "ws_" (escaped underscore -- `_` is a LIKE
# wildcard for "any single character"), e.g. "ws_3f9a21bc".
_WS_TEST_PATTERN = r"ws\_%"


def _test_pollution_filter():
    return or_(
        MarketplaceListing.source_workspace_id.like(_WS_TEST_PATTERN, escape="\\"),
        MarketplaceListing.source_workspace_id == "mp_src",
    )


async def clean_test_listings() -> tuple[int, int]:
    """Delete test-pollution listings. Returns (count_before, count_after)
    of TOTAL listings in the table (not just the deleted ones), so the
    caller can see the overall effect on the catalog."""
    async with SessionLocal() as db:
        count_before = await db.scalar(select(func.count()).select_from(MarketplaceListing))

        to_delete = await db.scalar(
            select(func.count())
            .select_from(MarketplaceListing)
            .where(_test_pollution_filter())
        )

        doomed_ids = (
            await db.scalars(
                select(MarketplaceListing.id).where(_test_pollution_filter())
            )
        ).all()
        if doomed_ids:
            # usage_events.listing_id has no ON DELETE CASCADE; clear it
            # first so the listing delete below doesn't hit a FK violation.
            await db.execute(
                delete(UsageEvent).where(UsageEvent.listing_id.in_(doomed_ids))
            )

        await db.execute(delete(MarketplaceListing).where(_test_pollution_filter()))
        await db.commit()

        count_after = await db.scalar(select(func.count()).select_from(MarketplaceListing))

    log.info(
        "clean_test_listings_complete",
        deleted=to_delete,
        count_before=count_before,
        count_after=count_after,
    )
    print(f"marketplace_listings before: {count_before}")
    print(f"deleted (test pollution):    {to_delete}")
    print(f"marketplace_listings after:  {count_after}")
    return count_before, count_after


def main() -> None:
    configure_logging()
    asyncio.run(clean_test_listings())


if __name__ == "__main__":
    main()
