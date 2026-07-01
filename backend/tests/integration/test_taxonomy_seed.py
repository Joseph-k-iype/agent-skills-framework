"""Integration tests for seed_taxonomy — idempotency and canonical coverage.

The fixture is ``graph_name`` (see ``tests/conftest.py``): it points the
module-level graph client singleton at a throwaway graph for the duration of
each test and deletes it afterwards.  The test overrides the integration-level
``_isolate_marketplace_listings`` autouse fixture with a no-op because this
file is graph-only and does not touch Postgres.
"""

from __future__ import annotations

import pytest

from app.db.seed_taxonomy import seed_taxonomy
from app.repositories.taxonomy_repo import TaxonomyRepository

pytestmark = pytest.mark.asyncio


# This file only touches FalkorDB — skip the Postgres cleanup autouse fixture.
@pytest.fixture(autouse=True)
async def _isolate_marketplace_listings():  # noqa: PT004
    yield


async def test_seed_idempotent(graph_name):
    n1 = await seed_taxonomy(graph_name)
    n2 = await seed_taxonomy(graph_name)
    assert n1 == n2 and n1 >= 22
    caps = await TaxonomyRepository(graph_name).list_tree("Capability")
    assert {t["key"] for t in caps} >= {"extraction", "extraction.table", "transformation.geocode"}
    assert all(t["status"] == "canonical" for t in caps)
