"""Marketplace listing persistence (PostgreSQL)."""

from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketplaceListing, SkillVersion, UsageEvent


class MarketplaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(
        self,
        *,
        source_workspace_id: str,
        source_path: str,
        version: str,
        title: str,
        summary: str | None,
        type: str | None,
        runtime: str | None,
        tags: list[str],
        author_id: uuid.UUID | None,
    ) -> MarketplaceListing:
        existing = await self.db.scalar(
            select(MarketplaceListing).where(
                MarketplaceListing.source_workspace_id == source_workspace_id,
                MarketplaceListing.source_path == source_path,
                MarketplaceListing.version == version,
            )
        )
        if existing:
            existing.title = title
            existing.summary = summary
            existing.type = type
            existing.runtime = runtime
            existing.tags = tags
            await self.db.flush()
            return existing
        row = MarketplaceListing(
            source_workspace_id=source_workspace_id,
            source_path=source_path,
            version=version,
            title=title,
            summary=summary,
            type=type,
            runtime=runtime,
            tags=tags,
            author_id=author_id,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def list(
        self,
        *,
        q: str | None = None,
        type: str | None = None,
        sort: str = "uses",
        limit: int = 100,
    ) -> list[MarketplaceListing]:
        stmt = select(MarketplaceListing).where(MarketplaceListing.is_public.is_(True))
        if type:
            stmt = stmt.where(MarketplaceListing.type == type)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(MarketplaceListing.title).like(like))
        order = {
            "recent": desc(MarketplaceListing.updated_at),
            "newest": desc(MarketplaceListing.created_at),
        }.get(sort, desc(MarketplaceListing.downloads))
        stmt = stmt.order_by(order, desc(MarketplaceListing.created_at)).limit(limit)
        return list((await self.db.scalars(stmt)).all())

    async def get(self, listing_id: uuid.UUID) -> MarketplaceListing | None:
        return await self.db.get(MarketplaceListing, listing_id)

    async def increment_downloads(self, listing_id: uuid.UUID) -> None:
        await self.db.execute(
            update(MarketplaceListing)
            .where(MarketplaceListing.id == listing_id)
            .values(downloads=MarketplaceListing.downloads + 1)
        )

    async def add_usage(
        self, *, listing_id: uuid.UUID, user_id: uuid.UUID | None, kind: str, meta: dict
    ) -> None:
        self.db.add(
            UsageEvent(listing_id=listing_id, user_id=user_id, kind=kind, meta=meta or {})
        )
        await self.db.flush()

    async def most_installed(self, *, limit: int = 10) -> list[MarketplaceListing]:
        stmt = (
            select(MarketplaceListing)
            .order_by(desc(MarketplaceListing.downloads))
            .limit(limit)
        )
        return list((await self.db.scalars(stmt)).all())

    async def next_version_number(self, listing_id: uuid.UUID) -> int:
        current = await self.db.scalar(
            select(func.max(SkillVersion.version)).where(SkillVersion.listing_id == listing_id)
        )
        return (current or 0) + 1

    async def version_for_sha(
        self, listing_id: uuid.UUID, content_sha: str
    ) -> SkillVersion | None:
        return await self.db.scalar(
            select(SkillVersion).where(
                SkillVersion.listing_id == listing_id,
                SkillVersion.content_sha == content_sha,
            )
        )

    async def get_version_by_sha(self, content_sha: str) -> SkillVersion | None:
        return await self.db.scalar(
            select(SkillVersion).where(SkillVersion.content_sha == content_sha)
        )

    async def add_version(
        self,
        *,
        listing_id: uuid.UUID,
        version: int,
        content_sha: str,
        content: str,
        changelog: str | None,
    ) -> SkillVersion:
        row = SkillVersion(
            listing_id=listing_id,
            version=version,
            content_sha=content_sha,
            content=content,
            changelog=changelog,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_versions(self, listing_id: uuid.UUID) -> list[SkillVersion]:
        stmt = (
            select(SkillVersion)
            .where(SkillVersion.listing_id == listing_id)
            .order_by(desc(SkillVersion.version))
        )
        return list((await self.db.scalars(stmt)).all())

    async def set_latest(
        self, listing_id: uuid.UUID, version: int, content_sha: str
    ) -> None:
        await self.db.execute(
            update(MarketplaceListing)
            .where(MarketplaceListing.id == listing_id)
            .values(latest_version=version, latest_sha=content_sha)
        )
