"""Authentication service — dev-admin + LDAP login, token issuance & refresh."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import UnauthorizedError
from app.auth.ldap_client import LdapClient, get_ldap_client
from app.auth.rbac import RoleName, permissions_for
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.models import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginResponse, TokenPair, UserProfile


class AuthService:
    def __init__(self, db: AsyncSession, ldap: LdapClient | None = None):
        self.db = db
        self.repo = UserRepository(db)
        self.ldap = ldap or get_ldap_client()

    # ── login ──
    async def login(self, username: str, password: str) -> LoginResponse:
        user = await self._authenticate(username, password)
        if user is None:
            raise UnauthorizedError("Invalid username or password")
        return await self._issue(user)

    async def _authenticate(self, username: str, password: str) -> User | None:
        # 1) dev-admin fallback (used when LDAP is disabled or for the local admin)
        if username == settings.dev_admin_username:
            user = await self.repo.get_by_username(username)
            if user and user.hashed_password and verify_password(password, user.hashed_password):
                return user
            return None

        # 2) LDAP
        identity = self.ldap.authenticate(username, password)
        if identity is None:
            return None
        role_name = self._map_group_to_role(identity.groups)
        role = await self.repo.get_role_by_name(role_name)
        if role is None:
            raise UnauthorizedError("Role mapping missing — contact an administrator")
        return await self.repo.upsert_ldap_user(
            username=identity.username,
            full_name=identity.full_name,
            ldap_dn=identity.dn,
            role=role,
        )

    @staticmethod
    def _map_group_to_role(groups: list[str]) -> str:
        for group in groups:
            mapped = settings.ldap_group_role_map.get(group)
            if mapped:
                return mapped
        return RoleName.CONSUMER

    # ── token issuance ──
    async def _issue(self, user: User) -> LoginResponse:
        perms = permissions_for(user.role.name)
        access = create_access_token(str(user.id), user.role.name, perms)
        refresh, exp = create_refresh_token(str(user.id))
        await self.repo.create_session(user.id, hash_token(refresh), exp)
        return LoginResponse(
            tokens=TokenPair(access_token=access, refresh_token=refresh),
            user=self._profile(user, perms),
        )

    @staticmethod
    def _profile(user: User, perms: list[str]) -> UserProfile:
        return UserProfile(
            id=str(user.id),
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            role=user.role.name,
            permissions=perms,
        )

    # ── refresh ──
    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise UnauthorizedError("Invalid refresh token") from None
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Not a refresh token")

        session = await self.repo.get_active_session(hash_token(refresh_token))
        if session is None:
            raise UnauthorizedError("Refresh token revoked or unknown")

        user = await self.repo.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User inactive")

        # rotate: revoke the old session, mint a new pair
        await self.repo.revoke_session(session, datetime.now(UTC))
        perms = permissions_for(user.role.name)
        access = create_access_token(str(user.id), user.role.name, perms)
        new_refresh, exp = create_refresh_token(str(user.id))
        await self.repo.create_session(user.id, hash_token(new_refresh), exp)
        return TokenPair(access_token=access, refresh_token=new_refresh)

    # ── current user profile ──
    async def me(self, user_id: str) -> UserProfile:
        import uuid

        user = await self.repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise UnauthorizedError("User not found")
        return self._profile(user, permissions_for(user.role.name))
