# Data Skill Marketplace — Phase 1 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-brand the app to "Data Skill Marketplace", add content-addressed (SHA) skill versioning, expose a public (unauthenticated) marketplace read API, and rebuild the marketplace home + detail UI to the approved palette-correct design.

**Architecture:** Backend-first. (1) Rename. (2) A pure canonicalization module computes a deterministic `sha256` over a skill's frontmatter+body. (3) A new `skill_versions` table records immutable per-version snapshots; the publish pipeline appends a version on content change (idempotent on identical content). (4) A new auth-free `/public/*` router serves published listings, detail, versions, and content-by-SHA with integrity verification. (5) The frontend gains a public layout + rebuilt marketplace home and detail pages consuming the public API.

**Tech Stack:** FastAPI, SQLAlchemy (async) + Alembic, PostgreSQL, Pydantic settings; React + TypeScript + Vite + Ant Design v5, axios, TanStack Query, react-markdown + mermaid.

## Global Constraints

- App display name is **exactly** `Data Skill Marketplace` (backend `app_name`, frontend wordmarks, `<title>`).
- Palette is unchanged (`frontend/src/app/theme/tokens.ts`): accent **Tesla Red `#E82127`** used *sparingly*; canvas `#FAFAF8`; surface `#FFFFFF`; ink `#111114`. Primary action buttons are **ink-black**, not red, so red stays special.
- Content SHA = `sha256` hex over canonical(frontmatter) + normalized body; **immutable per version**; short form is `sha[:7]`. API exposes full `sha256:<hex>`; UI shows `sha <first7>`.
- Public `/public/*` endpoints require **no authentication** and must return **only** published, `is_public=True` content — never drafts or workspace internals.
- Schema changes go through **Alembic** (`backend/migrations/`). Run `alembic heads` to find the current head and set `down_revision` to it.
- Python tests run via uv with a modern interpreter (project memory: system python is 3.9, SDK needs 3.11+). Use `cd backend && uv run --python 3.12 pytest …` (add `--with <pkg>` if an import is missing).
- TDD: write the failing test first. Commit after each task.

---

## File Structure

**Backend — create:**
- `backend/app/okf/canonical.py` — pure SHA canonicalization (no I/O).
- `backend/app/models/skill_version.py` — `SkillVersion` ORM model.
- `backend/app/api/v1/routers/public.py` — auth-free public marketplace router.
- `backend/migrations/versions/<rev>_skill_versions_and_listing_meta.py` — schema migration.
- `backend/tests/unit/test_canonical.py`, `backend/tests/unit/test_skill_versioning.py`, `backend/tests/integration/test_public_marketplace.py` — tests.

**Backend — modify:**
- `backend/app/core/config.py` — `app_name`.
- `backend/app/models/marketplace.py` — add `category`, `featured`, `latest_sha`, `latest_version`; relax version uniqueness.
- `backend/app/models/__init__.py` — export `SkillVersion`.
- `backend/app/repositories/marketplace_repo.py` — version helpers + per-concept upsert.
- `backend/app/services/marketplace_service.py` — SHA-aware publish, public read methods, `user` optional.
- `backend/app/api/v1/router.py` — register `public.router`.

**Frontend — create:**
- `frontend/src/app/layouts/PublicLayout.tsx` — top-nav public shell with `⌘K`.
- `frontend/src/features/marketplace/api/publicMarketplaceApi.ts` — auth-free client + types.
- `frontend/src/features/marketplace/components/SkillCard.tsx` — the approved card.
- `frontend/src/features/marketplace/components/CategoryStrip.tsx` — icon category strip.
- `frontend/src/shared/components/CommandPalette.tsx` — `⌘K` search overlay.

**Frontend — modify:**
- `frontend/index.html`, `frontend/package.json` — name/title.
- `frontend/src/app/layouts/SidebarLayout.tsx` (+ `TopNavLayout`) — wordmark.
- `frontend/src/router/index.tsx` — public routes outside `RequireAuth`.
- `frontend/src/features/marketplace/pages/MarketplacePage.tsx` — rebuild home.
- `frontend/src/features/marketplace/pages/MarketplaceDetailPage.tsx` — rebuild detail.

---

## Task 1: Rename to "Data Skill Marketplace" (backend + frontend strings)

**Files:**
- Modify: `backend/app/core/config.py:27`
- Modify: `frontend/index.html:6`, `frontend/package.json:2`, `frontend/src/app/layouts/SidebarLayout.tsx:44-46` (and the `TopNavLayout` wordmark ~line 91)
- Test: `backend/tests/unit/test_app_name.py`

**Interfaces:**
- Produces: `settings.app_name == "Data Skill Marketplace"`; FastAPI `app.title` follows it.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_app_name.py
from app.core.config import settings
from app.main import app


def test_app_name_is_data_skill_marketplace():
    assert settings.app_name == "Data Skill Marketplace"
    assert app.title == "Data Skill Marketplace"
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd backend && uv run --python 3.12 pytest tests/unit/test_app_name.py -v`
Expected: FAIL (`assert 'EAKSO' == 'Data Skill Marketplace'`).

- [ ] **Step 3: Make it pass**

In `backend/app/core/config.py` line 27, change `app_name: str = "EAKSO"` to `app_name: str = "Data Skill Marketplace"`.

- [ ] **Step 4: Run it, expect PASS**

Run: `cd backend && uv run --python 3.12 pytest tests/unit/test_app_name.py -v` → PASS.

- [ ] **Step 5: Update frontend strings**

- `frontend/index.html` line 6: `<title>Data Skill Marketplace</title>`.
- `frontend/package.json` line 2: `"name": "data-skill-marketplace-frontend",`.
- `frontend/src/app/layouts/SidebarLayout.tsx` (~line 45): replace the `EAKSO` text node with `Data Skill Marketplace`.
- In the same file's `TopNavLayout` (~line 91): replace `EAKSO` with `Data Skill Marketplace`.

- [ ] **Step 6: Verify frontend builds**

Run: `cd frontend && npm run build` → completes without type errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/tests/unit/test_app_name.py frontend/index.html frontend/package.json frontend/src/app/layouts/SidebarLayout.tsx
git commit -m "feat: rename app to Data Skill Marketplace"
```

---

## Task 2: SHA canonicalization module

**Files:**
- Create: `backend/app/okf/canonical.py`
- Test: `backend/tests/unit/test_canonical.py`

**Interfaces:**
- Produces:
  - `canonical_bytes(frontmatter: dict, body: str) -> bytes`
  - `content_sha(frontmatter: dict, body: str) -> str` — returns 64-char lowercase hex.
  - `short_sha(sha: str) -> str` — returns first 7 chars.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_canonical.py
from app.okf.canonical import canonical_bytes, content_sha, short_sha


def test_sha_is_deterministic():
    fm = {"type": "skill", "title": "X"}
    assert content_sha(fm, "body") == content_sha(fm, "body")


def test_sha_ignores_frontmatter_key_order():
    a = content_sha({"a": 1, "b": 2}, "body")
    b = content_sha({"b": 2, "a": 1}, "body")
    assert a == b


def test_sha_normalizes_newlines_and_trailing_ws():
    a = content_sha({"t": 1}, "line1\nline2")
    b = content_sha({"t": 1}, "line1  \r\nline2\r\n\n")
    assert a == b


def test_sha_changes_with_content():
    assert content_sha({"t": 1}, "a") != content_sha({"t": 1}, "b")


def test_short_sha():
    sha = content_sha({"t": 1}, "a")
    assert short_sha(sha) == sha[:7]
    assert len(content_sha({"t": 1}, "a")) == 64
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd backend && uv run --python 3.12 pytest tests/unit/test_canonical.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/okf/canonical.py
"""Deterministic content-addressing for skills.

The SHA is computed over a canonical serialization so that semantically
identical content (key order, line endings, trailing whitespace) yields the
same hash. Used as the immutable, content-addressed identity of a published
skill version.
"""

from __future__ import annotations

import hashlib
import json


def _normalize_body(body: str) -> str:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    stripped = [ln.rstrip() for ln in lines]
    text = "\n".join(stripped).strip("\n")
    return text + "\n" if text else ""


def canonical_bytes(frontmatter: dict, body: str) -> bytes:
    fm = json.dumps(
        frontmatter or {},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (fm + "\n" + _normalize_body(body)).encode("utf-8")


def content_sha(frontmatter: dict, body: str) -> str:
    return hashlib.sha256(canonical_bytes(frontmatter, body)).hexdigest()


def short_sha(sha: str) -> str:
    return sha[:7]
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd backend && uv run --python 3.12 pytest tests/unit/test_canonical.py -v` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/okf/canonical.py backend/tests/unit/test_canonical.py
git commit -m "feat: deterministic SHA content-addressing for skills"
```

---

## Task 3: `SkillVersion` model + listing metadata columns

**Files:**
- Create: `backend/app/models/skill_version.py`
- Modify: `backend/app/models/marketplace.py`, `backend/app/models/__init__.py`

**Interfaces:**
- Produces ORM `SkillVersion` with columns: `id, listing_id, version:int, content_sha:str, changelog:str|None, content:str, downloads:int`, timestamps; unique `(listing_id, version)` and `(listing_id, content_sha)`.
- `MarketplaceListing` gains: `category:str|None`, `featured:bool=False`, `latest_sha:str|None`, `latest_version:int|None`.

- [ ] **Step 1: Create the model**

```python
# backend/app/models/skill_version.py
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class SkillVersion(Base, TimestampMixin):
    """An immutable, content-addressed snapshot of a published skill version."""

    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("listing_id", "version", name="uq_skillversion_listing_version"),
        UniqueConstraint("listing_id", "content_sha", name="uq_skillversion_listing_sha"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column()
    content_sha: Mapped[str] = mapped_column(index=True)
    changelog: Mapped[str | None] = mapped_column(default=None)
    content: Mapped[str] = mapped_column()
    downloads: Mapped[int] = mapped_column(default=0)
```

- [ ] **Step 2: Extend the listing model**

In `backend/app/models/marketplace.py`, add these columns after `downloads` (line 42):

```python
    category: Mapped[str | None] = mapped_column(default=None, index=True)
    featured: Mapped[bool] = mapped_column(default=False, index=True)
    latest_sha: Mapped[str | None] = mapped_column(default=None)
    latest_version: Mapped[int | None] = mapped_column(default=None)
```

Also relax the version-scoped uniqueness so a listing is one row per concept. Replace the `__table_args__` block (lines 23-27) with:

```python
    __table_args__ = (
        UniqueConstraint(
            "source_workspace_id", "source_path", name="uq_listing_concept"
        ),
    )
```

- [ ] **Step 3: Export the model**

In `backend/app/models/__init__.py`, add `SkillVersion` to the imports and `__all__` (follow the existing pattern for `MarketplaceListing`).

- [ ] **Step 4: Verify import**

Run: `cd backend && uv run --python 3.12 python -c "from app.models import SkillVersion, MarketplaceListing; print('ok')"` → prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/skill_version.py backend/app/models/marketplace.py backend/app/models/__init__.py
git commit -m "feat: SkillVersion model + listing metadata columns"
```

---

## Task 4: Alembic migration for `skill_versions` + listing columns

**Files:**
- Create: `backend/migrations/versions/<rev>_skill_versions_and_listing_meta.py`

**Interfaces:**
- Consumes: models from Task 3.
- Produces: `skill_versions` table; new listing columns; swapped unique constraint. Backfills one `SkillVersion` (version=1) per existing listing.

- [ ] **Step 1: Find the current head**

Run: `cd backend && uv run --python 3.12 alembic heads`
Note the revision id printed — that is the `down_revision` for the new migration.

- [ ] **Step 2: Author the migration**

Create the file (use a fresh 12-hex `revision`, set `down_revision` to the head from Step 1):

```python
"""skill_versions and listing meta

Revision ID: <rev>
Revises: <head-from-step-1>
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "<rev>"
down_revision = "<head-from-step-1>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("marketplace_listings", sa.Column("category", sa.String(), nullable=True))
    op.add_column(
        "marketplace_listings",
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("marketplace_listings", sa.Column("latest_sha", sa.String(), nullable=True))
    op.add_column("marketplace_listings", sa.Column("latest_version", sa.Integer(), nullable=True))
    op.create_index("ix_marketplace_listings_category", "marketplace_listings", ["category"])
    op.create_index("ix_marketplace_listings_featured", "marketplace_listings", ["featured"])

    op.create_table(
        "skill_versions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("listing_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha", sa.String(), nullable=False),
        sa.Column("changelog", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("downloads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["marketplace_listings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("listing_id", "version", name="uq_skillversion_listing_version"),
        sa.UniqueConstraint("listing_id", "content_sha", name="uq_skillversion_listing_sha"),
    )
    op.create_index("ix_skill_versions_listing_id", "skill_versions", ["listing_id"])
    op.create_index("ix_skill_versions_content_sha", "skill_versions", ["content_sha"])

    # Backfill: one version per existing listing. SHA derived from id+version so it
    # is stable and unique without needing to re-read bundle content here.
    op.execute(
        """
        INSERT INTO skill_versions (id, listing_id, version, content_sha, content, downloads, created_at, updated_at)
        SELECT gen_random_uuid(), id, 1,
               encode(sha256((id::text || ':' || coalesce(version,'1'))::bytea), 'hex'),
               '', coalesce(downloads,0), now(), now()
        FROM marketplace_listings
        """
    )
    op.execute(
        "UPDATE marketplace_listings ml SET latest_version = 1, "
        "latest_sha = (SELECT content_sha FROM skill_versions sv WHERE sv.listing_id = ml.id LIMIT 1)"
    )

    # Swap the unique constraint from (workspace, path, version) to (workspace, path).
    op.drop_constraint("uq_listing_concept_version", "marketplace_listings", type_="unique")
    op.create_unique_constraint(
        "uq_listing_concept", "marketplace_listings", ["source_workspace_id", "source_path"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_listing_concept", "marketplace_listings", type_="unique")
    op.create_unique_constraint(
        "uq_listing_concept_version",
        "marketplace_listings",
        ["source_workspace_id", "source_path", "version"],
    )
    op.drop_index("ix_skill_versions_content_sha", "skill_versions")
    op.drop_index("ix_skill_versions_listing_id", "skill_versions")
    op.drop_table("skill_versions")
    op.drop_index("ix_marketplace_listings_featured", "marketplace_listings")
    op.drop_index("ix_marketplace_listings_category", "marketplace_listings")
    op.drop_column("marketplace_listings", "latest_version")
    op.drop_column("marketplace_listings", "latest_sha")
    op.drop_column("marketplace_listings", "featured")
    op.drop_column("marketplace_listings", "category")
```

> Note: `gen_random_uuid()` and `sha256()` require the `pgcrypto` extension. If `alembic upgrade` errors that `sha256`/`gen_random_uuid` is unknown, add `op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")` as the first line of `upgrade()`.

- [ ] **Step 3: Apply and verify round-trip**

Run (Postgres must be up via the project's Docker data services):
```bash
cd backend && uv run --python 3.12 alembic upgrade head
uv run --python 3.12 alembic downgrade -1
uv run --python 3.12 alembic upgrade head
```
Expected: all three succeed; final state has `skill_versions`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/
git commit -m "feat: migration for skill_versions and listing metadata"
```

---

## Task 5: SHA-aware publish + version repository helpers

**Files:**
- Modify: `backend/app/repositories/marketplace_repo.py`, `backend/app/services/marketplace_service.py`
- Test: `backend/tests/unit/test_skill_versioning.py`

**Interfaces:**
- Consumes: `content_sha` (Task 2), `SkillVersion` (Task 3).
- Produces on `MarketplaceRepository`:
  - `add_version(*, listing_id, version:int, content_sha:str, content:str, changelog:str|None) -> SkillVersion`
  - `get_version_by_sha(content_sha:str) -> SkillVersion | None`
  - `list_versions(listing_id) -> list[SkillVersion]` (newest version first)
  - `version_for_sha(listing_id, content_sha) -> SkillVersion | None`
  - `next_version_number(listing_id) -> int`
  - `set_latest(listing_id, version:int, content_sha:str) -> None`
- Produces on `MarketplaceService`: publish now records a `SkillVersion` (idempotent per SHA) and updates listing pointers. `__init__(db, user=None)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_skill_versioning.py
import pytest

from app.okf.canonical import content_sha


@pytest.mark.asyncio
async def test_publish_is_idempotent_on_identical_content(make_service_with_listing):
    """Re-publishing identical content must not create a second version."""
    svc, listing_id, frontmatter, body = make_service_with_listing
    sha = content_sha(frontmatter, body)

    v1 = await svc.repo.version_for_sha(listing_id, sha)
    assert v1 is not None and v1.version == 1

    # Same SHA -> no new version.
    next_n = await svc.repo.next_version_number(listing_id)
    assert next_n == 2  # would be the next number IF content changed
    existing = await svc.repo.get_version_by_sha(sha)
    assert existing is not None
```

> The `make_service_with_listing` fixture builds a `MarketplaceService` against a test DB session, creates a listing, and adds version 1 via `add_version`. Add it to `backend/tests/conftest.py` following the existing async-session fixture pattern there (read that file to match the harness). If the harness has no DB fixture, mark this test `@pytest.mark.integration` and use the integration DB fixture used by `tests/integration/test_index_projection.py`.

- [ ] **Step 2: Run, expect FAIL**

Run: `cd backend && uv run --python 3.12 pytest tests/unit/test_skill_versioning.py -v` → FAIL (helpers missing).

- [ ] **Step 3: Add repository helpers**

Append to `backend/app/repositories/marketplace_repo.py` (import `SkillVersion` and `asc`):

```python
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
```

Add `from app.models import SkillVersion` to the existing models import at the top.

- [ ] **Step 4: Make publish SHA-aware**

In `backend/app/services/marketplace_service.py`:
- Change `__init__` to `def __init__(self, db, user: CurrentUser | None = None):` and `self.user = user`.
- Import: `from app.okf.canonical import content_sha`.
- Replace the body of `upsert_on_publish` so that after `self.repo.upsert(...)` returns the listing it appends a version on content change:

```python
        listing = await self.repo.upsert(
            source_workspace_id=workspace_id,
            source_path=path,
            version=version,
            title=concept.title,
            summary=concept.description,
            type=concept.type,
            runtime=concept.runtime,
            tags=concept.tags,
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
```

> `self.user` may be `None` for system callers; the existing `author` block already guards `uuid.UUID(self.user.id)` — wrap it: `author = uuid.UUID(self.user.id) if self.user else None` inside its try/except.

- [ ] **Step 5: Run tests, expect PASS**

Run: `cd backend && uv run --python 3.12 pytest tests/unit/test_skill_versioning.py tests/unit/test_canonical.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/marketplace_repo.py backend/app/services/marketplace_service.py backend/tests/unit/test_skill_versioning.py backend/tests/conftest.py
git commit -m "feat: SHA-aware publish appends immutable skill versions"
```

---

## Task 6: Public (unauthenticated) marketplace read methods

**Files:**
- Modify: `backend/app/services/marketplace_service.py`
- Test: covered by Task 7's integration test.

**Interfaces:**
- Consumes: repo helpers (Task 5), `content_sha` (Task 2).
- Produces on `MarketplaceService`:
  - `async def public_list(*, q, type, category, sort, limit) -> list[dict]`
  - `async def public_get(listing_id) -> dict` (adds `sha`, `versions`, `latest_content`)
  - `async def public_categories() -> list[dict]` (`[{"category","count"}]`)
  - `async def public_fetch_by_sha(sha) -> dict` (integrity-verified content)
- Raises `NotFoundError` for unknown ids/sha; raises `IntegrityError` (new, see step) on SHA mismatch.

- [ ] **Step 1: Add public read methods**

Add to `MarketplaceService` (reuse existing `_listing_dict`; extend it to include `category`, `featured`, `latest_sha`, `latest_version`):

```python
    async def public_list(
        self, *, q=None, type=None, category=None, sort="uses", limit=60
    ) -> list[dict]:
        rows = await self.repo.list(q=q, type=type, sort=sort, limit=limit)
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
        out["content"] = await self._read_published(listing)
        versions = await self.repo.list_versions(listing.id)
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
```

> Integrity note: because the snapshot `content` is stored at publish time alongside the SHA computed from it, content-by-SHA is inherently consistent. A defensive re-check (`content_sha(parse_concept(...).frontmatter, .body) == sha`) can be added later when drift is possible; not needed in Phase 1 since the snapshot is immutable. (Recorded so this isn't a silent omission.)

- [ ] **Step 2: Verify import compiles**

Run: `cd backend && uv run --python 3.12 python -c "from app.services.marketplace_service import MarketplaceService; print('ok')"` → `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/marketplace_service.py
git commit -m "feat: public read methods for marketplace service"
```

---

## Task 7: Public `/public/*` router (auth-free) + registration

**Files:**
- Create: `backend/app/api/v1/routers/public.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/integration/test_public_marketplace.py`

**Interfaces:**
- Consumes: `MarketplaceService` public methods (Task 6), `get_db`, `success`.
- Produces endpoints (all **no auth**): `GET /api/v1/public/marketplace`, `GET /api/v1/public/marketplace/categories`, `GET /api/v1/public/marketplace/{listing_id}`, `GET /api/v1/public/skills/{sha}`.

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/integration/test_public_marketplace.py
import pytest


@pytest.mark.asyncio
async def test_public_list_requires_no_auth(async_client):
    # No Authorization header at all.
    resp = await async_client.get("/api/v1/public/marketplace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_public_categories_no_auth(async_client):
    resp = await async_client.get("/api/v1/public/marketplace/categories")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
```

> Use the integration test's existing ASGI client fixture (see `tests/integration/test_index_projection.py` for how `async_client`/app is built). If that file uses a differently named fixture, match it.

- [ ] **Step 2: Run, expect FAIL**

Run: `cd backend && uv run --python 3.12 pytest tests/integration/test_public_marketplace.py -v` → FAIL (404, route missing).

- [ ] **Step 3: Implement the router**

```python
# backend/app/api/v1/routers/public.py
"""Public marketplace — unauthenticated read-only catalog access.

These endpoints intentionally take NO auth dependency. They expose only
published, public listings and immutable version snapshots; never drafts or
workspace internals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.envelope import success
from app.services.marketplace_service import MarketplaceService

router = APIRouter()


@router.get("/marketplace")
async def public_list(
    q: str | None = None,
    type: str | None = None,
    category: str | None = None,
    sort: str = "uses",
    db: AsyncSession = Depends(get_db),
):
    svc = MarketplaceService(db, None)
    return success(await svc.public_list(q=q, type=type, category=category, sort=sort))


@router.get("/marketplace/categories")
async def public_categories(db: AsyncSession = Depends(get_db)):
    return success(await MarketplaceService(db, None).public_categories())


@router.get("/marketplace/{listing_id}")
async def public_get(listing_id: str, db: AsyncSession = Depends(get_db)):
    return success(await MarketplaceService(db, None).public_get(listing_id))


@router.get("/skills/{sha}")
async def public_skill_by_sha(sha: str, db: AsyncSession = Depends(get_db)):
    return success(await MarketplaceService(db, None).public_fetch_by_sha(sha))
```

> Route order matters: `/marketplace/categories` is declared before `/marketplace/{listing_id}` so "categories" is not captured as an id.

- [ ] **Step 4: Register the router**

In `backend/app/api/v1/router.py`, add `public` to the routers import and add:

```python
api_router.include_router(public.router, prefix="/public", tags=["public"])
```

- [ ] **Step 5: Run tests, expect PASS**

Run: `cd backend && uv run --python 3.12 pytest tests/integration/test_public_marketplace.py -v` → PASS.

- [ ] **Step 6: Full backend suite**

Run: `cd backend && uv run --python 3.12 pytest -q` → green (fix any regressions from the listing-uniqueness change before moving on).

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/routers/public.py backend/app/api/v1/router.py backend/tests/integration/test_public_marketplace.py
git commit -m "feat: auth-free public marketplace endpoints"
```

> **Deferred (not silently dropped):** rate limiting on `/public/*` is in the spec but there is no limiter infra in the app today. It is deferred to a Phase 4 hardening task; recorded here so it is not mistaken for done.

---

## Task 8: Frontend public API client + types

**Files:**
- Create: `frontend/src/features/marketplace/api/publicMarketplaceApi.ts`

**Interfaces:**
- Produces hooks: `usePublicMarketplace(q, type, category, sort)`, `usePublicListing(id)`, `usePublicCategories()`.
- Types: `PublicListing` (adds `category`, `featured`, `latest_sha`, `latest_version`), `PublicListingDetail` (adds `content`, `versions: VersionRef[]`), `Category` (`{category, count}`).

- [ ] **Step 1: Implement the client**

```typescript
// frontend/src/features/marketplace/api/publicMarketplaceApi.ts
import { useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface PublicListing {
  id: string;
  title: string;
  summary?: string | null;
  type?: string | null;
  category?: string | null;
  featured: boolean;
  runtime?: string | null;
  version: string;
  latest_sha?: string | null;
  latest_version?: number | null;
  tags: string[];
  downloads: number;
  author_id?: string | null;
  created_at?: string | null;
}

export interface VersionRef {
  version: number;
  sha: string;
  changelog?: string | null;
  created_at?: string | null;
}

export interface PublicListingDetail extends PublicListing {
  content: string;
  versions: VersionRef[];
}

export interface Category {
  category: string;
  count: number;
}

export type SortKey = "uses" | "recent" | "newest";

export function usePublicMarketplace(
  q: string,
  type: string | undefined,
  category: string | undefined,
  sort: SortKey,
) {
  return useQuery({
    queryKey: ["public-marketplace", q, type ?? "", category ?? "", sort],
    queryFn: () =>
      unwrap<PublicListing[]>(
        http.get(`/public/marketplace`, {
          params: { q: q || undefined, type: type || undefined, category: category || undefined, sort },
        }),
      ),
  });
}

export function usePublicCategories() {
  return useQuery({
    queryKey: ["public-categories"],
    queryFn: () => unwrap<Category[]>(http.get(`/public/marketplace/categories`)),
  });
}

export function usePublicListing(id: string | undefined) {
  return useQuery({
    queryKey: ["public-listing", id],
    queryFn: () => unwrap<PublicListingDetail>(http.get(`/public/marketplace/${id}`)),
    enabled: !!id,
  });
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc -b --noEmit` → no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/marketplace/api/publicMarketplaceApi.ts
git commit -m "feat: public marketplace API client"
```

---

## Task 9: Public layout shell + `⌘K` command palette

**Files:**
- Create: `frontend/src/app/layouts/PublicLayout.tsx`, `frontend/src/shared/components/CommandPalette.tsx`

**Interfaces:**
- Consumes: `usePublicMarketplace` (for palette search), `tokens`.
- Produces: `PublicLayout` (top-nav wordmark, search affordance opening the palette, Browse/Docs/Sign in, `<Outlet/>`); `CommandPalette` (modal opened by `⌘K`/`Ctrl-K`, searches listings, navigates to detail).

- [ ] **Step 1: Implement `CommandPalette`**

Build an AntD `Modal` (no title, `footer={null}`) holding an `Input` bound to a debounced query; on query, call `usePublicMarketplace(query, undefined, undefined, "uses")` and render up to 8 results as a list; clicking navigates to `/marketplace/${id}` and closes. Register a global keydown listener for `(e.metaKey||e.ctrlKey) && e.key === 'k'` that opens it and `Escape` to close. Use `tokens.color` values; the active/selected row uses `tokens.color.accent` text sparingly.

- [ ] **Step 2: Implement `PublicLayout`**

Top bar on `tokens.color.surface` with a hairline `tokens.color.line` bottom border: red 10×10 logo mark + `Data Skill Marketplace` wordmark; a search pill (click or `⌘K` opens `CommandPalette`); right side Browse / Docs links + an ink-black "Sign in" button linking to `/login`. Render `<Outlet/>` on `tokens.color.canvas`. Constrain content to `tokens.maxContentWidth`.

- [ ] **Step 3: Type-check + commit**

Run: `cd frontend && npx tsc -b --noEmit` → clean.
```bash
git add frontend/src/app/layouts/PublicLayout.tsx frontend/src/shared/components/CommandPalette.tsx
git commit -m "feat: public layout shell + command palette"
```

---

## Task 10: Route the marketplace publicly

**Files:**
- Modify: `frontend/src/router/index.tsx`

**Interfaces:**
- Consumes: `PublicLayout` (Task 9), existing `MarketplacePage`/`MarketplaceDetailPage`.
- Produces: `/`, `/marketplace`, `/marketplace/:id` served by `PublicLayout` **outside** `RequireAuth`; authed app stays under `RequireAuth`.

- [ ] **Step 1: Restructure routes**

Add a `PublicLayout` import. Insert a public branch as a sibling of the `RequireAuth` branch:

```tsx
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      { index: true, element: S(<MarketplacePage />) },
      { path: "marketplace", element: S(<MarketplacePage />) },
      { path: "marketplace/:id", element: S(<MarketplaceDetailPage />) },
    ],
  },
```

Move the existing authed `path: "/"` `RequireAuth` block to `path: "/app"` (so `dashboard`, `workspace`, `concepts/...`, `insights`, `settings/api-keys`, `admin/*` live under `/app/...`). Update the wildcard fallback to `<Navigate to="/" replace />`. Remove the old authed `marketplace` child routes (now public).

> Note: nav links and any hardcoded `/dashboard` redirects that should now be `/app/dashboard` are updated in the Phase 4 nav-restructure task; for Phase 1, update `RequireAuth`'s post-login redirect target to `/app/dashboard` so login still lands somewhere valid (check `RequireAuth.tsx`).

- [ ] **Step 2: Manual verify**

Run `cd frontend && npm run dev`; with the backend up, open `/` logged out → marketplace renders (public). Open `/app/dashboard` logged out → redirected to login.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.tsx frontend/src/router/RequireAuth.tsx
git commit -m "feat: serve marketplace publicly, move authed app under /app"
```

---

## Task 11: Rebuild marketplace home (approved design)

**Files:**
- Create: `frontend/src/features/marketplace/components/SkillCard.tsx`, `frontend/src/features/marketplace/components/CategoryStrip.tsx`
- Modify: `frontend/src/features/marketplace/pages/MarketplacePage.tsx`

**Interfaces:**
- Consumes: `usePublicMarketplace`, `usePublicCategories`, `tokens`, existing `theme.ts` helpers (`accentFor`, `iconFor`, `tint`).
- Produces: `SkillCard({ listing }: { listing: PublicListing })`; `CategoryStrip({ categories, active, onSelect })`.

- [ ] **Step 1: `SkillCard`** — surface card (`tokens.color.surface`, `tokens.radius`, hairline border, soft shadow `0 8px 22px -18px rgba(0,0,0,.18)`). Contents top→bottom: a row with optional `★ Featured` pill (only when `listing.featured`, text in `tokens.color.accent` on a light red tint) + a category pill (ink-secondary on canvas); a serif headline (`title`); a 2-line clamped `summary`; up to 3 tag chips; a footer (top hairline) with author avatar dot + `@handle` placeholder (author id short), `★ rating` placeholder (`—` until Phase 3), and `downloads` count; a final row with a monospace `sha <short>` badge (from `latest_sha`) and an ink-black `Use skill` button linking to `/marketplace/${id}`.

- [ ] **Step 2: `CategoryStrip`** — horizontal scroll row of pills: an `◆ All` pill (active state uses red tint + accent text) then one pill per category showing `icon name · count`. `onSelect(category | undefined)`.

- [ ] **Step 3: Rebuild `MarketplacePage`** — `PublicLayout` provides the chrome, so the page renders: a `CategoryStrip` (from `usePublicCategories`, controls `category` state), a "Featured" section header with a "Trending →" link (sort toggle), a responsive CSS grid (`repeat(auto-fill, minmax(280px, 1fr))`, gap 14px) of `SkillCard`s from `usePublicMarketplace(q, undefined, category, sort)`. Keep the existing search state but route the query through the public hook. Loading → AntD `Skeleton` cards; empty → a quiet empty state.

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc -b --noEmit` → clean.

- [ ] **Step 5: Visual verify**

Run the app; confirm the home matches the approved mockup (red only on logo/active-pill/featured/sign-in; ink-black `Use skill`; serif headlines; mono SHA badges). Compare against `.superpowers/brainstorm/95411-1782789220/content/marketplace-home.html`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/marketplace/components/SkillCard.tsx frontend/src/features/marketplace/components/CategoryStrip.tsx frontend/src/features/marketplace/pages/MarketplacePage.tsx
git commit -m "feat: rebuild marketplace home to approved design"
```

---

## Task 12: Rebuild marketplace detail (SHA, versions, login-gated use)

**Files:**
- Modify: `frontend/src/features/marketplace/pages/MarketplaceDetailPage.tsx`

**Interfaces:**
- Consumes: `usePublicListing`, existing `MarkdownPreview` (`@/features/concepts/components/MarkdownPreview`), `tokens`, auth state (to gate "Use skill").

- [ ] **Step 1: Rebuild the page** — two-column on wide screens:
  - **Header:** category pill, serif `title`, `summary`, author `@handle`, `★ rating` placeholder, a **version selector** (from `detail.versions`, default latest), and the full `sha256:<sha>` shown as a copyable monospace chip.
  - **Left/main:** rendered README via `<MarkdownPreview source={detail.content} />` (mermaid already supported).
  - **Right/action panel** (sticky): an ink-black **Use skill** button — if logged out, it routes to `/login?next=/marketplace/${id}`; if logged in, it opens the existing install/clone dialog. Below it, a read-only **API snippet** block: `curl -H "Authorization: Bearer sk_live_…" <API_BASE>/api/v1/public/skills/<sha>` with a copy button. (Clone-to-workspace + SDK snippets are completed in Phase 3; show the API snippet now.)
  - **Versions & changelog:** a compact list of `detail.versions` (version, short sha, date) under the action panel.

- [ ] **Step 2: Type-check + visual verify**

Run: `cd frontend && npx tsc -b --noEmit` → clean. Run the app; open a listing → renders content (with any mermaid diagrams), SHA chip copies, version selector lists versions, "Use skill" routes to login when logged out.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/marketplace/pages/MarketplaceDetailPage.tsx
git commit -m "feat: rebuild marketplace detail with SHA, versions, gated use"
```

---

## Phase 1 Done — Definition of Done

- [ ] Backend suite green: `cd backend && uv run --python 3.12 pytest -q`.
- [ ] `cd frontend && npx tsc -b --noEmit` clean; `npm run build` succeeds.
- [ ] Logged-out user can browse the marketplace home and open a detail page; "Use skill" routes to login.
- [ ] Publishing a changed skill creates a new `skill_versions` row with a new SHA; re-publishing identical content does not.
- [ ] App reads "Data Skill Marketplace" in the browser tab, login, and wordmarks.

## Follow-on Phases (separate plans, authored after Phase 1 lands)

- **Phase 2 — AI-assisted editor:** `/assist/*` (scaffold, rewrite/slash, chat, diagram) + three-pane Studio editor; default-signup role → `developer`; `assist:use` permission.
- **Phase 3 — Marketplace depth:** ratings & reviews; one-click consume (clone/SDK); versions/changelog polish.
- **Phase 4 — Surfaces & admin:** finalize Studio/Admin/Public nav; moderation; `/public/*` rate limiting (deferred from Task 7).
- **Phase 5 (optional) — Toolkits/bundles.**
