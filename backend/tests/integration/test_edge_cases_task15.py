"""Task 15 – deep edge-case coverage for the three gaps not already covered.

Cases covered here:
  3. Merge a proposed capability that TWO concepts use → both USES edges repoint;
     alias node gone.
  6. GET /api-keys/{id}/usage for a REVOKED key still returns historical events
     (revocation must NOT delete usage rows).
  8. seed_taxonomy + seed_marketplace run together on boot without collision.

Already-covered cases (not duplicated here):
  1. Both unknown capability AND source in one save → both proposed, save succeeds.
     → test_concept_references.py::test_unknown_capability_is_proposed_not_rejected
       passes capabilities=["totally.new.cap"] AND sources=["file.csv"] in one call.
  2. Reparenting leaves exactly one PARENT_OF edge (clear_parent works).
     → test_concept_hierarchy.py::test_reparenting_leaves_single_edge
  4. Faceted filter with nonexistent capability → [].
     → test_marketplace_facets.py::test_no_match_returns_empty_list
  5. add_usage from non-SDK marketplace path works with api_key_id=NULL.
     → test_per_key_usage.py::test_anonymous_usage_records_null_api_key_id
       calls mp.report_usage which internally calls repo.add_usage(api_key_id=None).
  7. /sdk/download is attachment/octet-stream and X-Checksum-SHA256 is correct.
     → test_sdk_download.py::test_download_content_disposition_is_attachment
        + test_sdk_download.py::test_download_checksum_header_matches_file
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _isolate_marketplace_listings():  # noqa: PT004
    """Override integration-conftest autouse: these tests clean up their own rows."""
    yield


async def _get_admin_id() -> str:
    from app.repositories.user_repo import UserRepository
    from app.db.session import SessionLocal

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


# ---------------------------------------------------------------------------
# Case 3: Merge a *proposed* capability that TWO concepts use
# ---------------------------------------------------------------------------


async def test_merge_proposed_capability_repoints_two_concept_uses_edges(graph_name):
    """merge_term repoints USES edges from BOTH concepts to the target; alias node gone."""
    from app.graph import client
    from app.repositories.taxonomy_repo import TaxonomyRepository

    repo = TaxonomyRepository()
    # Create alias (proposed) and canonical target
    await repo.upsert_term("Capability", "alias.cap", "Alias Cap", None, "proposed", None)
    await repo.upsert_term("Capability", "canonical.cap", "Canonical Cap", None, "canonical", None)

    # Wire two separate concept nodes to the alias via USES
    client.query(
        "MERGE (c1:Concept {key: 'concept.one'}) "
        "WITH c1 MATCH (t:Capability {key: 'alias.cap'}) "
        "MERGE (c1)-[:USES]->(t)"
    )
    client.query(
        "MERGE (c2:Concept {key: 'concept.two'}) "
        "WITH c2 MATCH (t:Capability {key: 'alias.cap'}) "
        "MERGE (c2)-[:USES]->(t)"
    )

    # Sanity: both edges exist before merge
    pre = client.query(
        "MATCH (c)-[:USES]->(t:Capability {key: 'alias.cap'}) RETURN c.key"
    ).result_set
    assert len(pre) == 2, f"expected 2 USES→alias edges before merge, got {len(pre)}"

    result = await repo.merge_term("Capability", "alias.cap", "canonical.cap")
    assert result is True

    # Alias node must be gone
    gone = await repo.get_term("Capability", "alias.cap")
    assert gone is None, "alias node must be deleted after merge"

    # Both concepts must now point to canonical.cap
    post = client.query(
        "MATCH (c)-[:USES]->(t:Capability {key: 'canonical.cap'}) "
        "RETURN c.key ORDER BY c.key"
    ).result_set
    repointed_keys = [row[0] for row in post]
    assert "concept.one" in repointed_keys, f"concept.one not repointed; got {repointed_keys}"
    assert "concept.two" in repointed_keys, f"concept.two not repointed; got {repointed_keys}"

    # No residual USES edges to the (now-deleted) alias
    stale = client.query(
        "MATCH (c)-[:USES]->(t:Capability {key: 'alias.cap'}) RETURN c.key"
    ).result_set
    assert not stale, f"stale USES→alias edges remain: {stale}"


# ---------------------------------------------------------------------------
# Case 6: GET /api-keys/{id}/usage for a REVOKED key still returns history
# ---------------------------------------------------------------------------


async def _seed_listing_for_revoke_test(admin_id: str) -> str:
    """Create a minimal published listing; return its id."""
    from app.api.deps import CurrentUser
    from app.auth.rbac import RoleName, permissions_for
    from app.db.session import SessionLocal
    from app.services.concept_service import ConceptService
    from app.services.marketplace_service import MarketplaceService

    u = CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )
    async with SessionLocal() as db:
        cs = ConceptService(db, u)
        await cs.create(
            workspace_id="t15_revoke_src",
            folder_path="",
            name="Revoke Test Skill",
            type="skill",
            description="revoked key usage test",
            runtime=None,
            tags=[],
            capabilities=[],
            body="# Revoke\nUsage history.",
            frontmatter={},
        )
        path = "revoke-test-skill.md"
        await cs.publish(workspace_id="t15_revoke_src", path=path, version="1.0.0")
        mp = MarketplaceService(db, u)
        listings = await mp.list_listings(q=None, type=None)
        row = next(x for x in listings if x["source_path"] == path)
        listing_id = row["id"]
        await db.commit()

    return listing_id


async def test_revoked_key_usage_endpoint_still_returns_history(monkeypatch, tmp_path):
    """After revoking a key, GET /api-keys/{id}/usage returns historical usage (HTTP 200)."""
    from app.graph import client
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes
    bootstrap_indexes()

    admin_id = await _get_admin_id()
    listing_id = await _seed_listing_for_revoke_test(admin_id)

    from app.db.session import SessionLocal
    from app.services.api_key_service import ApiKeyService
    from app.repositories.marketplace_repo import MarketplaceRepository

    # Create a key, record two usage events, then revoke the key.
    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="revoke-hist-key")
        await db.commit()
        key_id = created["id"]
        raw_key = created["key"]

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        for _ in range(3):
            await repo.add_usage(
                listing_id=uuid.UUID(listing_id),
                user_id=uuid.UUID(admin_id),
                kind="fetch",
                meta={},
                api_key_id=uuid.UUID(key_id),
            )
        await db.commit()

    # Revoke the key
    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        await svc.revoke(user_id=admin_id, key_id=key_id)
        await db.commit()

    # Authenticate with the raw key must now return (None, None)
    async with SessionLocal() as db:
        owner, _ = await ApiKeyService(db).authenticate(raw_key)
    assert owner is None, "revoked key must not authenticate"

    # But GET /api-keys/{id}/usage (owner-JWT-authed) must still return the 3 events.
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.security import create_access_token

    token = create_access_token(admin_id, "developer", [])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            f"/api/v1/api-keys/{key_id}/usage",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, (
        f"Expected 200 for revoked key usage, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()["data"]
    assert data["total"] == 3, f"Expected 3 historical events, got {data['total']}"
    assert data["by_kind"].get("fetch", 0) == 3

    # Cleanup: remove the test listing's usage events + listing
    async with SessionLocal() as db:
        from sqlalchemy import delete
        from app.models import UsageEvent, MarketplaceListing
        await db.execute(
            delete(UsageEvent).where(UsageEvent.listing_id == uuid.UUID(listing_id))
        )
        await db.execute(
            delete(MarketplaceListing).where(MarketplaceListing.id == uuid.UUID(listing_id))
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Case 8: seed_taxonomy + seed_marketplace run together without collision
# ---------------------------------------------------------------------------


async def test_seed_taxonomy_and_seed_marketplace_together(graph_name):
    """Calling seed_taxonomy then seed_marketplace_demo in sequence (as boot does) is collision-free."""
    from app.db.seed_taxonomy import seed_taxonomy
    from app.db.seed_marketplace import seed_marketplace_demo
    from app.db.session import SessionLocal
    from app.repositories.taxonomy_repo import TaxonomyRepository
    from sqlalchemy import select, delete
    from app.models import MarketplaceListing, UsageEvent

    # Snapshot existing marketplace listings BEFORE the test seeds anything
    async with SessionLocal() as db:
        before_ids = set((await db.scalars(select(MarketplaceListing.id))).all())

    # Step 1: seed taxonomy (graph-only, idempotent)
    n1 = await seed_taxonomy(graph_name)
    assert n1 >= 22, f"seed_taxonomy should return ≥22 terms, got {n1}"

    # Step 2: seed marketplace (Postgres, idempotent)
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)
        await db.commit()

    # Step 3: run both again — no duplicate listings, no error
    n2 = await seed_taxonomy(graph_name)
    assert n1 == n2, "seed_taxonomy is not idempotent — duplicate terms created"

    async with SessionLocal() as db:
        await seed_marketplace_demo(db)
        await db.commit()

    # After double-run: taxonomy term count unchanged
    repo = TaxonomyRepository(graph_name)
    caps = await repo.list_tree("Capability")
    assert {t["key"] for t in caps} >= {"extraction", "transformation.geocode"}

    # Marketplace listing count must not have grown from the second run
    async with SessionLocal() as db:
        after_ids = set((await db.scalars(select(MarketplaceListing.id))).all())

    new_ids = after_ids - before_ids
    # Cleanup: remove only the rows this test created
    if new_ids:
        async with SessionLocal() as db:
            await db.execute(
                delete(UsageEvent).where(UsageEvent.listing_id.in_(new_ids))
            )
            await db.execute(
                delete(MarketplaceListing).where(MarketplaceListing.id.in_(new_ids))
            )
            await db.commit()

    # Verify idempotency: a third run adds zero new rows
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)
        await db.commit()

    async with SessionLocal() as db:
        final_ids = set((await db.scalars(select(MarketplaceListing.id))).all())

    assert final_ids == after_ids, (
        f"seed_marketplace_demo is not idempotent: {len(final_ids - after_ids)} extra rows on 3rd run"
    )
