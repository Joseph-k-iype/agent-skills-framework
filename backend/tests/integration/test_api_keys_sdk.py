"""API key lifecycle (create/list/authenticate/revoke) backing SDK auth."""

from __future__ import annotations

import uuid

import pytest

from app.db.session import SessionLocal
from app.services.api_key_service import ApiKeyService

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


async def test_create_returns_key_once_then_authenticates(admin_id):
    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="ci-key")
        await db.commit()
        assert created["key"].startswith("sk_live_")
        assert created["prefix"] == created["key"][:14]

        # The plaintext authenticates to the owning user + its key id.
        owner, api_key_id = await svc.authenticate(created["key"])
        await db.commit()
        assert str(owner) == admin_id
        assert str(api_key_id) == created["id"]

        # Listing never exposes the secret, only the prefix.
        listed = await svc.list(user_id=admin_id)
        row = next(k for k in listed if k["id"] == created["id"])
        assert "key" not in row and row["prefix"] == created["prefix"]


async def test_revoked_key_no_longer_authenticates(admin_id):
    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="to-revoke")
        await db.commit()
        await svc.revoke(user_id=admin_id, key_id=created["id"])
        await db.commit()
        assert await svc.authenticate(created["key"]) == (None, None)


async def test_bad_key_authenticates_to_none(admin_id):
    async with SessionLocal() as db:
        assert await ApiKeyService(db).authenticate("sk_live_not_a_real_key") == (None, None)


# ---------------------------------------------------------------------------
# Per-key usage aggregation (Task 10)
# ---------------------------------------------------------------------------

@pytest.fixture
async def second_user_id() -> str:
    """Create a second user (not admin) in-test to verify ownership isolation.

    We do NOT rely on a seeded 'developer' user so this test runs unconditionally
    in CI without requiring ``make seed``.  The user is created with a unique
    username derived from a UUID to avoid collisions with any existing seed data.
    """
    import uuid as _uuid
    from sqlalchemy import delete
    from app.core.security import hash_password
    from app.models import User
    from app.repositories.user_repo import UserRepository

    username = f"ci_second_user_{_uuid.uuid4().hex[:8]}"

    async with SessionLocal() as db:
        repo = UserRepository(db)
        # Resolve the 'developer' role (must already exist from seed or migrations)
        role = await repo.get_role_by_name("developer")
        assert role is not None, "Role 'developer' not found — ensure migrations/seed ran"
        user = User(
            username=username,
            full_name="CI Second User",
            hashed_password=hash_password("ci-test-pw"),
            role_id=role.id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)

    yield user_id

    # Teardown: remove the ephemeral user to keep the DB clean
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.username == username))
        await db.commit()


async def _seed_usage_events(admin_id: str, key_id: str, listing_id: str, count: int = 2) -> None:
    """Insert ``count`` 'fetch' usage events for the given key/listing pair."""
    from app.repositories.marketplace_repo import MarketplaceRepository

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        for _ in range(count):
            await repo.add_usage(
                listing_id=uuid.UUID(listing_id),
                user_id=uuid.UUID(admin_id),
                kind="fetch",
                meta={},
                api_key_id=uuid.UUID(key_id),
            )
        await db.commit()


async def _seed_listing(admin_id: str) -> str:
    """Create a minimal marketplace listing; return its id."""
    from app.auth.rbac import RoleName, permissions_for
    from app.api.deps import CurrentUser
    from app.services.concept_service import ConceptService
    from app.services.marketplace_service import MarketplaceService
    from app.storage import paths

    u = CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )
    async with SessionLocal() as db:
        cs = ConceptService(db, u)
        await cs.create(
            workspace_id="t10_src",
            folder_path="",
            name="Task10 Skill",
            type="skill",
            description="task 10 usage test",
            runtime=None,
            tags=[],
            capabilities=[],
            body="# Task10\nUsage.",
            frontmatter={},
        )
        path = "task10-skill.md"
        await cs.publish(workspace_id="t10_src", path=path, version="1.0.0")
        mp = MarketplaceService(db, u)
        listings = await mp.list_listings(q=None, type=None)
        row = next(x for x in listings if x["source_path"] == path)
        await db.commit()
        return row["id"]


async def test_usage_endpoint_returns_aggregated_counts(admin_id, monkeypatch, tmp_path):
    """Owner GETs /api-keys/{id}/usage → total==2, by_kind has fetch count."""
    from app.graph import client
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes
    bootstrap_indexes()

    listing_id = await _seed_listing(admin_id)

    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="usage-test-key")
        await db.commit()
        key_id = created["id"]

    await _seed_usage_events(admin_id, key_id, listing_id, count=2)

    from app.repositories.api_key_repo import ApiKeyRepository
    from app.repositories.marketplace_repo import MarketplaceRepository

    async with SessionLocal() as db:
        key_repo = ApiKeyRepository(db)
        mp_repo = MarketplaceRepository(db)
        usage = await mp_repo.get_usage_for_key(uuid.UUID(key_id))

    assert usage["total"] == 2
    assert usage["by_kind"].get("fetch", 0) == 2
    assert isinstance(usage["by_skill"], list)
    assert isinstance(usage["recent"], list)
    assert len(usage["recent"]) <= 20


async def test_usage_endpoint_404_for_wrong_owner(admin_id, second_user_id):
    """A different user fetching another user's key_id → 404 (ownership gate)."""
    from app.repositories.api_key_repo import ApiKeyRepository
    from app.repositories.marketplace_repo import MarketplaceRepository

    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="admin-key-other-test")
        await db.commit()
        key_id = uuid.UUID(created["id"])

    # Verify ownership check: key belongs to admin_id, not second_user_id.
    async with SessionLocal() as db:
        key_repo = ApiKeyRepository(db)
        key = await key_repo.get(key_id)
        assert key is not None
        assert str(key.user_id) == admin_id
        # second_user_id should NOT be the owner
        assert str(key.user_id) != second_user_id

    # Simulate what the endpoint does: check ownership, expect None for wrong owner.
    async with SessionLocal() as db:
        key_repo = ApiKeyRepository(db)
        owned = await key_repo.get_for_user(key_id, uuid.UUID(second_user_id))
        assert owned is None, "Non-owner must not get the key (→ 404)"


async def test_usage_endpoint_via_http(admin_id, monkeypatch, tmp_path):
    """Full HTTP round-trip: owner calls GET /api-keys/{id}/usage after 2 events."""
    from app.graph import client
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes
    bootstrap_indexes()

    listing_id = await _seed_listing(admin_id)

    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="http-usage-key")
        await db.commit()
        key_id = created["id"]

    await _seed_usage_events(admin_id, key_id, listing_id, count=2)

    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.security import create_access_token

    token = create_access_token(admin_id, "developer", [])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            f"/api/v1/api-keys/{key_id}/usage",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    assert data["by_kind"]["fetch"] == 2


async def test_usage_endpoint_404_http_wrong_owner(admin_id, second_user_id):
    """Wrong owner gets HTTP 404 when requesting another user's key usage."""
    async with SessionLocal() as db:
        svc = ApiKeyService(db)
        created = await svc.create(user_id=admin_id, name="admin-key-404-test")
        await db.commit()
        key_id = created["id"]

    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.security import create_access_token

    token = create_access_token(second_user_id, "developer", [])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            f"/api/v1/api-keys/{key_id}/usage",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404
