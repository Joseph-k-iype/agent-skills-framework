"""Marketplace — a storefront of published concept versions, consumed by the SDK.

A listing is created when a concept version is published. External apps fetch a
skill's content via the SDK (API-key authed) and report usage back; the files in
their workspace bundles stay the source of truth. This service serves the catalog
and the published content + tracks usage.
"""

from __future__ import annotations

import uuid

from app.api.deps import CurrentUser
from app.api.errors import NotFoundError
from app.okf.canonical import content_sha
from app.okf.concept import parse_concept
from app.repositories.marketplace_repo import MarketplaceRepository
from app.storage import paths
from app.storage.repo import BundleRepo


def _publish_tag(source_path: str, version: str) -> str:
    return f"{paths.slugify(source_path.removesuffix('.md'))}-v{version}"


def _listing_dict(listing) -> dict:
    return {
        "id": str(listing.id),
        "source_workspace_id": listing.source_workspace_id,
        "source_path": listing.source_path,
        "title": listing.title,
        "summary": listing.summary,
        "type": listing.type,
        "runtime": listing.runtime,
        "version": listing.version,
        "tags": listing.tags or [],
        "capabilities": listing.capabilities or [],
        "sources": listing.sources or [],
        "downloads": listing.downloads,
        "author_id": str(listing.author_id) if listing.author_id else None,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "category": listing.category,
        "featured": listing.featured,
        "latest_sha": listing.latest_sha,
        "latest_version": listing.latest_version,
    }


class MarketplaceService:
    def __init__(self, db, user: CurrentUser | None = None):
        self.db = db
        self.user = user
        self.repo = MarketplaceRepository(db)

    async def upsert_on_publish(
        self, *, workspace_id: str, path: str, version: str
    ) -> None:
        """Create/refresh the catalog entry for a freshly published concept version,
        and append an immutable SkillVersion when the content actually changed
        (idempotent on identical content)."""
        bundle = BundleRepo(workspace_id)
        concept = parse_concept(path, bundle.read_file(path))
        author = None
        try:
            author = uuid.UUID(self.user.id) if self.user else None
        except (ValueError, TypeError):
            author = None
        listing = await self.repo.upsert(
            source_workspace_id=workspace_id,
            source_path=path,
            version=version,
            title=concept.title,
            summary=concept.description,
            type=concept.type,
            runtime=concept.runtime,
            tags=concept.tags,
            capabilities=getattr(concept, "capabilities", []) or [],
            sources=getattr(concept, "sources", []) or [],
            author_id=author,
        )
        sha = content_sha(concept.frontmatter, concept.body)
        existing = await self.repo.version_for_sha(listing.id, sha)
        if existing is None:
            n = await self.repo.next_version_number(listing.id)
            await self.repo.add_version(
                listing_id=listing.id,
                version=n,
                content_sha=sha,
                content=bundle.read_file(path),
                changelog=None,
            )
            await self.repo.set_latest(listing.id, n, sha)

    async def list_listings(
        self,
        *,
        q: str | None,
        type: str | None,
        capability: str | None = None,
        source: str | None = None,
        sort: str = "uses",
    ) -> list[dict]:
        return [
            _listing_dict(x)
            for x in await self.repo.list(
                q=q, type=type, capability=capability, source=source, sort=sort
            )
        ]

    async def get_listing(self, listing_id: str) -> dict:
        listing = await self.repo.get(uuid.UUID(listing_id))
        if not listing:
            raise NotFoundError("Listing not found")
        out = _listing_dict(listing)
        # Preview the published content at its tag (falls back to current file).
        bundle = BundleRepo(listing.source_workspace_id)
        tag = _publish_tag(listing.source_path, listing.version)
        try:
            out["content"] = bundle.read_file_at(listing.source_path, tag)
        except Exception:
            out["content"] = (
                bundle.read_file(listing.source_path)
                if bundle.exists_file(listing.source_path)
                else ""
            )
        return out

    async def _read_published(self, listing) -> str:
        bundle = BundleRepo(listing.source_workspace_id)
        tag = _publish_tag(listing.source_path, listing.version)
        try:
            return bundle.read_file_at(listing.source_path, tag)
        except Exception:
            return bundle.read_file(listing.source_path) if bundle.exists_file(
                listing.source_path
            ) else ""

    async def fetch_skill(self, *, listing_id: str, user_id: str | None) -> dict:
        """SDK consumption: return a published skill's content + a usable system prompt."""
        listing = await self.repo.get(uuid.UUID(listing_id))
        if not listing:
            raise NotFoundError("Listing not found")
        raw = await self._read_published(listing)
        concept = parse_concept(listing.source_path, raw)
        system_prompt = (
            "You are an assistant equipped with the following skill. Apply it to answer the "
            f"user's task.\n\n# Skill: {concept.title}\n{concept.body}"
        )
        await self.repo.add_usage(
            listing_id=listing.id,
            user_id=uuid.UUID(user_id) if user_id else None,
            kind="fetch",
            meta={},
        )
        return {
            "id": str(listing.id),
            "source_path": listing.source_path,
            "title": concept.title,
            "type": listing.type,
            "version": listing.version,
            "content": raw,
            "body": concept.body,
            "system_prompt": system_prompt,
        }

    async def public_list(
        self,
        *,
        q=None,
        type=None,
        category=None,
        capability: str | None = None,
        source: str | None = None,
        sort="uses",
        limit=60,
    ) -> list[dict]:
        rows = await self.repo.list(
            q=q, type=type, capability=capability, source=source, sort=sort, limit=limit
        )
        if category:
            rows = [r for r in rows if (r.category or r.type) == category]
        return [_listing_dict(x) for x in rows]

    async def public_categories(self) -> list[dict]:
        rows = await self.repo.list(limit=1000)
        counts: dict[str, int] = {}
        for r in rows:
            key = r.category or r.type or "Other"
            counts[key] = counts.get(key, 0) + 1
        return sorted(
            [{"category": k, "count": v} for k, v in counts.items()],
            key=lambda d: (-d["count"], d["category"]),
        )

    async def public_get(self, listing_id: str) -> dict:
        listing = await self.repo.get(uuid.UUID(listing_id))
        if not listing or not listing.is_public:
            raise NotFoundError("Listing not found")
        out = _listing_dict(listing)
        versions = await self.repo.list_versions(listing.id)
        latest_content = versions[0].content if versions and versions[0].content else None
        out["content"] = latest_content if latest_content else await self._read_published(listing)
        out["versions"] = [
            {
                "version": v.version,
                "sha": v.content_sha,
                "changelog": v.changelog,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]
        return out

    async def public_fetch_by_sha(self, sha: str) -> dict:
        version = await self.repo.get_version_by_sha(sha)
        if version is None:
            raise NotFoundError("Skill version not found")
        listing = await self.repo.get(version.listing_id)
        if not listing or not listing.is_public:
            raise NotFoundError("Listing not found")
        return {
            "sha": version.content_sha,
            "version": version.version,
            "title": listing.title,
            "type": listing.type,
            "content": version.content,
        }

    async def report_usage(
        self, *, listing_id: str, user_id: str | None, kind: str = "apply", meta: dict | None = None
    ) -> dict:
        listing = await self.repo.get(uuid.UUID(listing_id))
        if not listing:
            raise NotFoundError("Listing not found")
        await self.repo.add_usage(
            listing_id=listing.id,
            user_id=uuid.UUID(user_id) if user_id else None,
            kind=kind,
            meta=meta or {},
        )
        if kind == "apply":
            await self.repo.increment_downloads(listing.id)  # "uses" counter
        return {"ok": True}
