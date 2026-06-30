"""Shared FastAPI dependencies: DB/graph handles, current user, RBAC guards."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import SessionLocal

bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@dataclass
class CurrentUser:
    id: str
    role: str
    permissions: list[str]

    def has(self, code: str) -> bool:
        return code in self.permissions


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if creds is None:
        raise UnauthorizedError("Missing bearer token")
    try:
        payload = decode_token(creds.credentials)
    except ValueError:
        raise UnauthorizedError("Invalid or expired token") from None
    if payload.get("type") != "access":
        raise UnauthorizedError("Not an access token")
    return CurrentUser(
        id=payload["sub"],
        role=payload.get("role", ""),
        permissions=payload.get("perms", []),
    )


def require_permission(code: str):
    """Tier-level guard: the caller's role must grant ``code``."""

    async def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has(code):
            raise ForbiddenError(f"Missing permission: {code}")
        return user

    return _dep


async def require_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Authenticate an SDK request by API key (``Authorization: Bearer sk_live_…``)."""
    from app.auth.rbac import permissions_for
    from app.repositories.user_repo import UserRepository
    from app.services.api_key_service import ApiKeyService

    if creds is None or not creds.credentials.startswith("sk_"):
        raise UnauthorizedError("Missing or malformed API key")
    user_id = await ApiKeyService(db).authenticate(creds.credentials)
    if user_id is None:
        raise UnauthorizedError("Invalid or revoked API key")
    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("API key owner not found")
    role = user.role.name if user.role else ""
    return CurrentUser(id=str(user.id), role=role, permissions=permissions_for(role))


def client_meta(request: Request) -> dict[str, str | None]:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
