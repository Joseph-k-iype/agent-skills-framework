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


# Override the integration-level autouse fixture that requires Postgres — these
# tests are graph-only and do not touch the marketplace_listings table.
@pytest.fixture(autouse=True)
async def _isolate_marketplace_listings():  # noqa: PT004
    yield


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


# ---------------------------------------------------------------------------
# merge_term tests
# ---------------------------------------------------------------------------


async def test_merge_repoints_uses_edge(graph_name):
    """Capability alias used by a Concept via USES is repointed to the target."""
    from app.graph import client

    repo = TaxonomyRepository()
    # Create two capability terms
    await repo.upsert_term("Capability", "a.keep", "Keep", None, "canonical", None)
    await repo.upsert_term("Capability", "a.dup", "Dup", None, "canonical", None)
    # Create a concept and wire a USES edge to the alias
    client.query(
        "MERGE (c:Concept {key: 'c.uses'}) "
        "WITH c "
        "MATCH (t:Capability {key: 'a.dup'}) "
        "MERGE (c)-[:USES]->(t)"
    )

    result = await repo.merge_term("Capability", "a.dup", "a.keep")
    assert result is True

    # alias must be gone
    gone = await repo.get_term("Capability", "a.dup")
    assert gone is None

    # USES edge must now point to a.keep
    rows = client.query(
        "MATCH (c:Concept {key: 'c.uses'})-[:USES]->(t:Capability {key: 'a.keep'}) RETURN c"
    ).result_set
    assert rows, "expected USES edge pointing to a.keep"


async def test_merge_preserves_derived_from_edge(graph_name):
    """DERIVED_FROM edge type is preserved after merge (not silently converted to USES)."""
    from app.graph import client

    repo = TaxonomyRepository()
    await repo.upsert_term("Source", "s.keep", "Keep", None, "canonical", None)
    await repo.upsert_term("Source", "s.dup", "Dup", None, "canonical", None)
    # Wire DERIVED_FROM concept→alias
    client.query(
        "MERGE (c:Concept {key: 'c.derived'}) "
        "WITH c "
        "MATCH (t:Source {key: 's.dup'}) "
        "MERGE (c)-[:DERIVED_FROM]->(t)"
    )

    result = await repo.merge_term("Source", "s.dup", "s.keep")
    assert result is True

    # alias gone
    assert await repo.get_term("Source", "s.dup") is None

    # DERIVED_FROM must point to s.keep
    rows = client.query(
        "MATCH (c:Concept {key: 'c.derived'})-[:DERIVED_FROM]->(t:Source {key: 's.keep'}) RETURN c"
    ).result_set
    assert rows, "expected DERIVED_FROM edge pointing to s.keep"

    # must NOT have a USES edge (edge type must be preserved)
    wrong = client.query(
        "MATCH (c:Concept {key: 'c.derived'})-[:USES]->(t:Source {key: 's.keep'}) RETURN c"
    ).result_set
    assert not wrong, "DERIVED_FROM must not be converted to USES"


async def test_merge_reparents_hierarchy_children(graph_name):
    """Children of the alias become children of the merge target."""
    from app.graph import client

    repo = TaxonomyRepository()
    await repo.upsert_term("Capability", "parent.keep", "Keep", None, "canonical", None)
    await repo.upsert_term("Capability", "parent.dup", "Dup", None, "canonical", None)
    await repo.upsert_term(
        "Capability", "child.node", "Child", None, "canonical", "parent.dup"
    )

    result = await repo.merge_term("Capability", "parent.dup", "parent.keep")
    assert result is True

    # alias gone
    assert await repo.get_term("Capability", "parent.dup") is None

    # child.node should now have parent.keep as its parent
    tree = await repo.list_tree("Capability")
    by_key = {t["key"]: t.get("parent_key") for t in tree}
    assert by_key.get("child.node") == "parent.keep", (
        f"child.node parent should be 'parent.keep', got {by_key.get('child.node')!r}"
    )


async def test_merge_missing_into_key_returns_false(graph_name):
    """merge_term returns False when the into_key does not exist; alias is intact."""
    repo = TaxonomyRepository()
    await repo.upsert_term("Capability", "a.alias", "Alias", None, "canonical", None)

    result = await repo.merge_term("Capability", "a.alias", "nonexistent.key")
    assert result is False

    # alias must still exist
    term = await repo.get_term("Capability", "a.alias")
    assert term is not None
    assert term["key"] == "a.alias"
