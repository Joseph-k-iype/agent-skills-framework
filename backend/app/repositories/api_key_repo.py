"""API key persistence (PostgreSQL)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey


class ApiKeyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(
        self, *, user_id: uuid.UUID, name: str, prefix: str, key_hash: str
    ) -> ApiKey:
        row = ApiKey(user_id=user_id, name=name, prefix=prefix, key_hash=key_hash)
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_for_user(self, user_id: uuid.UUID) -> list[ApiKey]:
        stmt = (
            select(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.revoked_at.is_(None))
            .order_by(ApiKey.created_at.desc())
        )
        return list((await self.db.scalars(stmt)).all())

    async def by_hash(self, key_hash: str) -> ApiKey | None:
        return await self.db.scalar(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
        )

    async def get(self, key_id: uuid.UUID) -> ApiKey | None:
        return await self.db.get(ApiKey, key_id)

    async def get_for_user(self, key_id: uuid.UUID, user_id: uuid.UUID) -> ApiKey | None:
        """Return the key only if it belongs to ``user_id``; else ``None``.

        Deliberately does NOT filter on ``revoked_at`` so that revoked keys
        still expose their historical usage data.
        """
        return await self.db.scalar(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.user_id == user_id,
            )
        )
