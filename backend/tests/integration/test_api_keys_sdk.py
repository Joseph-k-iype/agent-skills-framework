"""API key lifecycle (create/list/authenticate/revoke) backing SDK auth."""

from __future__ import annotations

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

        # The plaintext authenticates to the owning user.
        owner = await svc.authenticate(created["key"])
        await db.commit()
        assert str(owner) == admin_id

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
        assert await svc.authenticate(created["key"]) is None


async def test_bad_key_authenticates_to_none(admin_id):
    async with SessionLocal() as db:
        assert await ApiKeyService(db).authenticate("sk_live_not_a_real_key") is None
