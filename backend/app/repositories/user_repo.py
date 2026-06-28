"""User & Session persistence (PostgreSQL)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role, Session, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        return (
            await self.db.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        return (await self.db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()

    async def upsert_ldap_user(
        self, username: str, full_name: str | None, ldap_dn: str, role: Role
    ) -> User:
        user = await self.get_by_username(username)
        if user is None:
            user = User(username=username, full_name=full_name, ldap_dn=ldap_dn, role_id=role.id)
            self.db.add(user)
        else:
            user.full_name = full_name or user.full_name
            user.ldap_dn = ldap_dn
            user.role_id = role.id
        await self.db.flush()
        return user

    # ── sessions / refresh tokens ──
    async def create_session(
        self, user_id: uuid.UUID, refresh_token_hash: str, expires_at: datetime
    ) -> Session:
        s = Session(user_id=user_id, refresh_token_hash=refresh_token_hash, expires_at=expires_at)
        self.db.add(s)
        await self.db.flush()
        return s

    async def get_active_session(self, refresh_token_hash: str) -> Session | None:
        return (
            await self.db.execute(
                select(Session).where(
                    Session.refresh_token_hash == refresh_token_hash,
                    Session.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    async def revoke_session(self, session: Session, when: datetime) -> None:
        session.revoked_at = when
        await self.db.flush()
