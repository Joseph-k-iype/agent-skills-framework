"""Marketplace listing persistence (PostgreSQL)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Text, cast, desc, func, or_, select, update
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
        capabilities: list[str],
        sources: list[str],
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
            existing.capabilities = capabilities
            existing.sources = sources
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
            capabilities=capabilities,
            sources=sources,
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
        capability: str | None = None,
        source: str | None = None,
        sort: str = "uses",
        limit: int = 100,
    ) -> list[MarketplaceListing]:
        stmt = select(MarketplaceListing).where(MarketplaceListing.is_public.is_(True))
        if type:
            stmt = stmt.where(MarketplaceListing.type == type)
        if q:
            like = f"%{q.lower()}%"
            # Match title OR summary OR any tag. ``tags`` is a JSONB array
            # (e.g. ["csv", "graph"]); casting it to text and lower-matching
            # against it is a simple substring check that works for our
            # short, single-word tag vocabulary without needing to unnest
            # the array in SQL.
            stmt = stmt.where(
                or_(
                    func.lower(MarketplaceListing.title).like(like),
                    func.lower(MarketplaceListing.summary).like(like),
                    func.lower(cast(MarketplaceListing.tags, Text)).like(like),
                )
            )
        if capability:
            # Substring match on the JSONB-cast text: hierarchy-inclusive by design
            # (e.g. "extraction" also matches "extraction.table"), NOT exact-match.
            like = f"%{capability.lower()}%"
            stmt = stmt.where(
                func.lower(cast(MarketplaceListing.capabilities, Text)).like(like)
            )
        if source:
            # Same substring / hierarchy-inclusive match as for capability above.
            like = f"%{source.lower()}%"
            stmt = stmt.where(
                func.lower(cast(MarketplaceListing.sources, Text)).like(like)
            )
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
        self,
        *,
        listing_id: uuid.UUID,
        user_id: uuid.UUID | None,
        kind: str,
        meta: dict,
        api_key_id: uuid.UUID | None = None,
    ) -> None:
        self.db.add(
            UsageEvent(
                listing_id=listing_id,
                user_id=user_id,
                kind=kind,
                meta=meta or {},
                api_key_id=api_key_id,
            )
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

    async def get_usage_for_key(self, api_key_id: uuid.UUID) -> dict[str, Any]:
        """Aggregate usage_events rows for a given api_key_id.

        Returns::

            {
                "total": int,
                "last_used_at": str | None,   # ISO-8601
                "by_kind": {kind: count, ...},
                "by_skill": [{"listing_id": str, "title": str, "count": int}, ...],
                "recent": [{"kind": str, "listing_id": str, "created_at": str}, ...],
            }
        """
        # ---- total + last_used_at ----
        agg = await self.db.execute(
            select(
                func.count(UsageEvent.id).label("total"),
                func.max(UsageEvent.created_at).label("last_used_at"),
            ).where(UsageEvent.api_key_id == api_key_id)
        )
        row = agg.one()
        total: int = row.total or 0
        last_used_at = row.last_used_at.isoformat() if row.last_used_at else None

        # ---- by_kind ----
        kind_rows = await self.db.execute(
            select(UsageEvent.kind, func.count(UsageEvent.id).label("cnt"))
            .where(UsageEvent.api_key_id == api_key_id)
            .group_by(UsageEvent.kind)
        )
        by_kind: dict[str, int] = {r.kind: r.cnt for r in kind_rows}

        # ---- by_skill (join to listing for title) ----
        # Inner-join intentionally excludes events with NULL listing_id; those are
        # counted in `total`/`by_kind` but are not skill-scoped so they don't
        # appear here (sum(by_skill[*].count) may be less than total).
        skill_rows = await self.db.execute(
            select(
                UsageEvent.listing_id,
                MarketplaceListing.title,
                func.count(UsageEvent.id).label("cnt"),
            )
            .join(MarketplaceListing, MarketplaceListing.id == UsageEvent.listing_id)
            .where(UsageEvent.api_key_id == api_key_id)
            .group_by(UsageEvent.listing_id, MarketplaceListing.title)
            .order_by(desc(func.count(UsageEvent.id)))
        )
        by_skill = [
            {"listing_id": str(r.listing_id), "title": r.title, "count": r.cnt}
            for r in skill_rows
        ]

        # ---- recent (up to 20 most-recent events) ----
        recent_rows = await self.db.execute(
            select(UsageEvent.kind, UsageEvent.listing_id, UsageEvent.created_at)
            .where(UsageEvent.api_key_id == api_key_id)
            .order_by(desc(UsageEvent.created_at))
            .limit(20)
        )
        recent = [
            {
                "kind": r.kind,
                "listing_id": str(r.listing_id),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_rows
        ]

        return {
            "total": total,
            "last_used_at": last_used_at,
            "by_kind": by_kind,
            "by_skill": by_skill,
            "recent": recent,
        }
