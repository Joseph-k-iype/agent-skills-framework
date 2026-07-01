# Implementation Plan — Per-Skill Stats & Clone (Workstream B)

**Spec:** `docs/superpowers/specs/2026-07-01-per-skill-stats-clone-design.md`
**Branch:** `feat/skill-stats-clone`

Test commands (discovered):
- Backend: `cd backend && uv run --python 3.12 --extra dev pytest <path> -q` (runs against live PG + FalkorDB; integration tests self-clean listings).
- Frontend: `cd frontend && npx vitest run <path>` ; typecheck `npx tsc --noEmit` ; build `npm run build`.

Each task: write failing test → run (fails) → implement → run (passes) → commit.

---

## Task 1 — `clones` column + migration

**Model** `backend/app/models/marketplace.py`: add after `downloads`:
```python
    clones: Mapped[int] = mapped_column(default=0)
```

**Migration** `backend/migrations/versions/a5e6f7a8b9c0_listing_clones.py` (down_revision = `f4d5e6f7a8b9`):
```python
"""listing_clones

Revision ID: a5e6f7a8b9c0
Revises: f4d5e6f7a8b9
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a5e6f7a8b9c0"
down_revision = "f4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketplace_listings",
        sa.Column("clones", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("marketplace_listings", "clones")
```

Verify: `cd backend && uv run --python 3.12 --extra dev alembic upgrade head`.
Add `clones` to `_listing_dict` in `marketplace_service.py`.
Commit: `feat(marketplace): clones column + migration`.

## Task 2 — repo `uses_cumulative` + `increment_clones`

Test `backend/tests/integration/test_skill_stats.py::test_uses_cumulative_*`: seed listing + apply events across days incl. before window; assert cumulative includes pre-window offset, ends at total; empty → `[]`.

Impl in `marketplace_repo.py`:
- `increment_clones(listing_id)` mirrors `increment_downloads`.
- `uses_cumulative(listing_id, days=90)`: `offset` = count of apply events before window start; grouped daily counts within window via `func.date_trunc('day', created_at)`; running sum + offset; always append a final "today" point at current total; `[]` when no apply events at all.

Commit: `feat(marketplace): uses_cumulative + increment_clones repo methods`.

## Task 3 — `MarketplaceService.clone_to_workspace` + `uses_history`

Test `test_skill_stats.py::test_clone_to_workspace_*`: clone creates concept w/ provenance frontmatter, increments clones, logs `kind="clone"` event; version defaults to latest; missing listing → NotFoundError.

Impl: load listing + version content (latest via `list_versions`), call `ConceptService.create(...)` with provenance frontmatter (`source_listing_id`, `source_sha`, `cloned_from`, `cloned_at`), `increment_clones`, `add_usage(kind="clone")`, return `{workspace_id, path}`. Add `uses_history(listing_id, days)` passthrough that 404s non-public.

Commit: `feat(marketplace): clone_to_workspace service + history passthrough`.

## Task 4 — endpoints

Public `public.py`: `GET /marketplace/{listing_id}/history?days=90` → series; `clones` already in detail via `_listing_dict`.
Auth `marketplace.py`: `POST /{listing_id}/clone` guarded `require_permission("skill:create")`, body pydantic model.

Test `test_public_marketplace.py` (history), `test_marketplace_clone.py` (unauth 401/403; auth 200 returns `{workspace_id, path}`).
Commit: `feat(marketplace): clone + history endpoints`.

## Task 5 — frontend api

`publicMarketplaceApi.ts`: `clones` on `PublicListingDetail`; `HistoryPoint`; `useListingHistory(id, days=90)`.
`marketplaceApi.ts`: `useCloneListing()` mutation.
Commit: `feat(fe): marketplace stats + clone api hooks`.

## Task 6 — components (each w/ Vitest test)

`StatStrip.tsx`, `DownloadHistoryChart.tsx` (recharts AreaChart, empty state on `[]`, mock recharts in test), `CloneModal.tsx` (submit calls mutation with `{workspace_id, folder_path, name, version}`; unauth → `/login?next=` redirect).
Commit each.

## Task 7 — wire into `MarketplaceDetailPage.tsx`

Stat strip under header, chart under README, "Clone to workspace" button opens `CloneModal` (replaces the "coming in a later phase" note). Page test.
Commit: `feat(fe): wire stats + clone into detail page`.

## Task 8 — verification

Backend pytest (marketplace subset + full), `npx vitest run`, `npx tsc --noEmit`, `npm run build`. Report counts.
