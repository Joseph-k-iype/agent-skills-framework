"""Idempotent seeding: permissions, roles, role→permission links, dev admin.

Run via ``python -m app.db.seed`` (see Makefile ``seed`` target). Safe to run
repeatedly — it upserts and never duplicates.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import (
    PERMISSIONS,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    RoleName,
)
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.seed_marketplace import seed_marketplace_demo
from app.db.session import SessionLocal
from app.models import Permission, Role, User

log = get_logger("seed")


async def _seed_permissions(db: AsyncSession) -> dict[str, Permission]:
    existing = {p.code: p for p in (await db.execute(select(Permission))).scalars()}
    for code, desc in PERMISSIONS.items():
        if code not in existing:
            p = Permission(code=code, description=desc)
            db.add(p)
            existing[code] = p
    await db.flush()
    return existing


async def _seed_roles(db: AsyncSession, perms: dict[str, Permission]) -> dict[str, Role]:
    existing = {r.name: r for r in (await db.execute(select(Role))).scalars()}
    for name in (RoleName.CONSUMER, RoleName.DEVELOPER, RoleName.ADMIN):
        role = existing.get(name)
        if role is None:
            role = Role(name=name, description=ROLE_DESCRIPTIONS[name])
            db.add(role)
            existing[name] = role
        # reconcile permission set
        role.permissions = [perms[c] for c in ROLE_PERMISSIONS[name]]
    await db.flush()
    return existing


async def _seed_dev_admin(db: AsyncSession, roles: dict[str, Role]) -> None:
    username = settings.dev_admin_username
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    admin_role = roles[RoleName.ADMIN]
    if user is None:
        db.add(
            User(
                username=username,
                full_name="Local Administrator",
                is_dev_admin=True,
                hashed_password=hash_password(settings.dev_admin_password),
                role_id=admin_role.id,
            )
        )
        log.info("dev_admin_created", username=username)
    else:
        # keep password in sync with the configured value
        user.hashed_password = hash_password(settings.dev_admin_password)
        user.role_id = admin_role.id
        user.is_dev_admin = True


async def seed() -> None:
    async with SessionLocal() as db:
        perms = await _seed_permissions(db)
        roles = await _seed_roles(db, perms)
        await _seed_dev_admin(db, roles)
        await db.commit()
    log.info("seed_complete", permissions=len(PERMISSIONS), roles=3)

    # Demo marketplace catalog — independently idempotent, own session/commit.
    async with SessionLocal() as db:
        await seed_marketplace_demo(db)


def main() -> None:
    configure_logging()
    asyncio.run(seed())


if __name__ == "__main__":
    main()
