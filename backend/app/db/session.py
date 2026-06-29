"""Async engine + session factory + FastAPI dependency."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Under pytest, each test runs in its own event loop. A process-wide connection
# pool would hand a later loop a connection bound to an earlier (now closed)
# loop, which asyncpg cannot terminate cleanly. NullPool opens/closes a
# connection per checkout — entirely within the current loop — so tests stay
# isolated. Production keeps normal pooling with pre-ping.
if "pytest" in sys.modules:
    engine = create_async_engine(settings.database_url, future=True, poolclass=NullPool)
else:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
