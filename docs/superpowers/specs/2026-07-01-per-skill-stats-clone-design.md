# Per-Skill Stats & Clone — Design Spec

**Date:** 2026-07-01
**Branch:** `feat/skill-stats-clone`
**Status:** Approved (pending spec review) — ready for implementation planning
**Builds on:** the public marketplace (`MarketplaceListing`, `SkillVersion`, `UsageEvent`),
`MarketplaceService`, `ConceptService.create`, and the recharts usage in `InsightsPage`.
**Roadmap position:** Workstream **B** of the six-part marketplace build
(A rich editor ✓ → **B per-skill stats/clone** → C home ranking + lazy load →
D OTel/Grafana → E framework adapters → F design studio).

## 1. Summary

Enrich the per-skill marketplace detail page with a **prominent stat strip**
(total uses · clones · versions/latest · created/updated), a **cumulative
usage-over-time chart**, and a working **"Clone to workspace"** action that copies
a skill into the user's workspace with provenance and clone tracking. Requires new
backend aggregation + clone endpoints and one small schema addition; the frontend
adds a chart component and a clone modal.

## 2. Decisions (locked with user)

- **History chart:** **cumulative total uses over time** (running curve), with a
  day range (default 90).
- **Clone:** **copy + provenance + track** — copy the selected version's content into
  a chosen workspace/folder as a new concept, stamp provenance, and record the clone.
  Login required.
- **Stat strip:** all four — **total uses, clones, versions & latest, created & updated**.

## 3. Backend

### 3.1 Schema (one migration)
Add `clones: int` (default 0, not null) to `marketplace_listings`. Alembic migration
mirrors the existing `downloads` column. `UsageEvent.kind` gains a third value,
`"clone"` (no enum change needed — `kind` is a free `str`).

### 3.2 Cumulative history query
`MarketplaceRepository.uses_cumulative(listing_id, days=90) -> list[dict]`:
- Bucket `usage_events` rows for the listing with `kind='apply'` by day
  (`date_trunc('day', created_at)`), for the last `days` days.
- Compute `offset` = count of `apply` events **before** the window start.
- Return an ordered series `[{ "date": "YYYY-MM-DD", "cumulative": int }]` where each
  point is `offset + running_sum(daily_counts up to that day)`. Days with no events
  are omitted (frontend area chart interpolates between points); the series always
  includes a final point at "today" so the curve ends at the current total.
- Empty history returns `[]`.

### 3.3 Endpoints
- **Public (unauthenticated), in `public.py`:**
  `GET /public/marketplace/{listing_id}/history?days=90`
  → `[{date, cumulative}]`. 404 if listing missing/not public.
  The existing `GET /public/marketplace/{listing_id}` detail response gains `clones: int`.
- **Authenticated, in `marketplace.py`:**
  `POST /marketplace/{listing_id}/clone`, guarded by `require_permission("skill:create")`.
  Body: `{ workspace_id: str, folder_path?: str, name?: str, version?: int }`.
  Behavior (in a new `MarketplaceService.clone_to_workspace(...)`):
  1. Load the listing + the requested version (default: latest) and its `content`/`sha`.
  2. Call `ConceptService.create(workspace_id, folder_path or "", name or <slug of title>,
     type=listing.type, description=listing.summary, runtime=listing.runtime,
     tags=listing.tags, capabilities=listing.capabilities, sources=listing.sources,
     body=content, frontmatter={ ...provenance })`.
  3. Provenance in `frontmatter`: `source_listing_id`, `source_sha`, `cloned_from`
     (title), `cloned_at` (ISO). No concept-storage schema change — provenance rides
     in the concept frontmatter.
  4. `repo.increment_clones(listing_id)` and `repo.add_usage(listing_id, user_id,
     kind="clone", meta={"workspace_id":..., "version":...})`.
  5. Return `{ workspace_id, path }` of the created concept so the client can navigate
     to it.
  Errors: 404 if listing/version missing; 409 (or the existing conflict envelope) if a
  concept already exists at the target path — surfaced from `ConceptService.create`.

## 4. Frontend (`features/marketplace`)

- **`publicMarketplaceApi.ts`**: `PublicListingDetail` gains `clones: number`; add
  `useListingHistory(id, days=90)` (query → `HistoryPoint[]`).
- **`marketplaceApi.ts`** (authenticated): add `useCloneListing()` mutation →
  `POST /marketplace/{id}/clone`, invalidating the listing + workspace concept list on
  success.
- **`components/DownloadHistoryChart.tsx`**: recharts `AreaChart` of `{date, cumulative}`,
  Swiss-minimal styling from `tokens`; empty-state message when the series is empty.
- **`components/StatStrip.tsx`**: four compact stats (uses, clones, versions+latest,
  created+updated) rendered from the detail response.
- **`components/CloneModal.tsx`**: workspace picker (reuse `features/workspace/api`
  workspace list), folder + name inputs, version select; calls `useCloneListing`; on
  success toasts and offers a link to the new concept. Unauthenticated users hitting
  "Clone" are redirected via the existing `/login?next=/marketplace/{id}` pattern.
- **`MarketplaceDetailPage.tsx`**: mount the stat strip below the header, the chart in
  the main column under the README, and wire the "Clone to workspace" button (replacing
  the "Clone … coming in a later phase" note) to open `CloneModal`.

## 5. Testing (TDD; repo conventions — pytest backend, Vitest frontend)

- **Backend**
  - `uses_cumulative`: seed `apply` events across several days (+ some before the
    window) → asserts ordered cumulative values include the pre-window offset and end
    at the current total; empty case returns `[]`.
  - `clone_to_workspace`: creates a concept with the listing content + provenance
    frontmatter, increments `clones`, logs a `kind="clone"` usage event; version
    defaulting to latest; missing listing/version → error.
  - Clone endpoint: unauthenticated → 401/403; authenticated with `skill:create` →
    200 and returns `{workspace_id, path}`.
- **Frontend**
  - `StatStrip`: renders all four values from a fixture.
  - `DownloadHistoryChart`: renders from mocked points; shows empty state on `[]`.
  - `CloneModal`: submitting calls the mutation with `{workspace_id, folder_path,
    name, version}`; unauthenticated path triggers the login redirect.

## 6. Files touched

- Backend: `models/marketplace.py` (+`clones`), a new Alembic migration,
  `repositories/marketplace_repo.py` (+`uses_cumulative`, `increment_clones`),
  `services/marketplace_service.py` (+`clone_to_workspace`, history passthrough),
  `api/v1/routers/public.py` (+history endpoint, +`clones` in detail),
  `api/v1/routers/marketplace.py` (+clone endpoint).
- Frontend: `api/publicMarketplaceApi.ts`, `api/marketplaceApi.ts`,
  `components/DownloadHistoryChart.tsx`, `components/StatStrip.tsx`,
  `components/CloneModal.tsx`, `pages/MarketplaceDetailPage.tsx` (+ their tests).

## 7. Out of scope (future workstreams)

Home ranking + infinite scroll and the fancycomponents library (C), OTel/Grafana
observability (D), framework adapters (E), design studio (F). Sorting the marketplace
list by clones and per-version download breakdowns are deferred unless trivial.
