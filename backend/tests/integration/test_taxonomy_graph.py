"""Integration tests for TaxonomyRepository against a real FalkorDB instance.

NOTE: The brief specifies a ``graph`` fixture parameter.  The actual fixture in
this codebase is named ``graph_name`` (see ``tests/conftest.py``).  We use
``graph_name`` here — it isolates each test in a throwaway graph that is
deleted after the test completes, exactly as specified.
"""

from __future__ import annotations

import pytest

from app.repositories.taxonomy_repo import TaxonomyRepository

pytestmark = pytest.mark.asyncio


async def test_upsert_and_tree(graph_name):
    repo = TaxonomyRepository()
    await repo.upsert_term("Capability", "extraction", "Extraction", None, "canonical", None)
    await repo.upsert_term(
        "Capability", "extraction.table", "Table extraction", None, "canonical", "extraction"
    )
    tree = await repo.list_tree("Capability")
    keys = {t["key"]: t.get("parent_key") for t in tree}
    assert keys["extraction"] is None
    assert keys["extraction.table"] == "extraction"


async def test_unknown_term_proposed_then_promote(graph_name):
    repo = TaxonomyRepository()
    await repo.upsert_term("Source", "weird.src", "Weird", None, "proposed", None)
    proposed = await repo.list_proposed()
    assert any(t["key"] == "weird.src" and t["status"] == "proposed" for t in proposed)
    await repo.promote("Source", "weird.src")
    t = await repo.get_term("Source", "weird.src")
    assert t["status"] == "canonical"
