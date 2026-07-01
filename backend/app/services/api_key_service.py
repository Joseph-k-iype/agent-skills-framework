"""API keys for the SDK / programmatic access.

A key is ``sk_live_<random>``. We store only its sha256 hash plus a short visible
prefix; the plaintext is returned exactly once at creation. Authentication hashes
the presented key and looks it up.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from app.repositories.api_key_repo import ApiKeyRepository


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate() -> tuple[str, str]:
    """Return ``(full_key, prefix)``."""
    full = f"sk_live_{secrets.token_urlsafe(24)}"
    return full, full[:14]


class ApiKeyService:
    def __init__(self, db):
        self.db = db
        self.repo = ApiKeyRepository(db)

    async def create(self, *, user_id: str, name: str) -> dict:
        full, prefix = _generate()
        row = await self.repo.add(
            user_id=uuid.UUID(user_id), name=name, prefix=prefix, key_hash=_hash(full)
        )
        return {
            "id": str(row.id),
            "name": row.name,
            "prefix": row.prefix,
            "key": full,  # shown once
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def list(self, *, user_id: str) -> list[dict]:
        rows = await self.repo.list_for_user(uuid.UUID(user_id))
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "prefix": r.prefix,
                "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def revoke(self, *, user_id: str, key_id: str) -> None:
        row = await self.repo.get(uuid.UUID(key_id))
        if row and str(row.user_id) == user_id:
            row.revoked_at = datetime.now(UTC)
            await self.db.flush()

    async def authenticate(
        self, presented_key: str
    ) -> tuple[uuid.UUID, uuid.UUID] | tuple[None, None]:
        """Return ``(user_id, api_key_id)`` for a valid key, else ``(None, None)``.
        Bumps last_used on success.
        """
        row = await self.repo.by_hash(_hash(presented_key))
        if not row:
            return (None, None)
        row.last_used_at = datetime.now(UTC)
        await self.db.flush()
        return (row.user_id, row.id)
