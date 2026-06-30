# Storefront Swiss Uplift + Data Hygiene — Implementation Plan

> **For agentic workers:** executed via superpowers:subagent-driven-development (fresh subagent per task + review). Checkbox steps track progress.

**Goal:** Replace the cluttered marketplace home with a Swiss-design hero-search + Pinterest masonry, fix the duplicated-skills problem (test-data pollution), seed varied real demo skills, and harden tests so they stop polluting the dev DB.

**Architecture:** Backend first (clean + seed real content, harden tests, broaden search) so the redesigned UI renders against good data; then the frontend Swiss redesign (a shared storefront style module → SkillCard → hero+masonry home → detail header); then screenshot-based visual verification.

**Tech Stack:** FastAPI/SQLAlchemy/Postgres; React/TS/Vite/AntD.

## Root cause of "duplicated skills"
The dev DB held 18 listings titled "Lineage Tracker" with identical `source_path` but distinct random `source_workspace_id` (`ws_xxxxxxxx`). These are **integration-test artifacts**: the publishing test creates a listing in a fresh random workspace each run and the shared dev DB has no rollback, so rows accumulate. Not a model bug — test pollution + missing real seed content.

## Global Constraints (Swiss design system — single source of truth)

- **Palette unchanged** (`frontend/src/app/theme/tokens.ts`): ink `#111114`, ink2 `#5B5B61`, ink3 `#8A8A90`, canvas `#FAFAF8`, surface `#FFFFFF`, line `#ECECE8`, lineStrong `#DEDEDA`. **Tesla Red `#E82127` is the ONLY accent — functional markers only** (active filter, featured tick), never fills/decoration. Primary buttons are ink-black.
- **Category color** is demoted to a single **8px square swatch** next to an uppercase mono category label (reuse `TYPE_ACCENT` from `features/marketplace/theme.ts`). No full-width color bands, no gradients.
- **Type:** NO serif. Display/titles = Inter (system sans stack from `tokens.font.sans`), weight 600, letter-spacing `-0.02em`. Body = Inter 400, 13px, line-height 1.55, ink2. **All data (SHA, counts, category code) = monospace** (`tokens.font.mono`), 10–11px, ink3. The monospace content-address is the typographic signature.
- **Surface:** near-sharp corners (**4px radius**), **hairline 1px borders, NO drop shadows**. Hover = border darken to `lineStrong` (no shadow lift). Flat author marks (mono initials or `@handle` text — no gradient circles).
- **Hero:** centered, max-width 560px search input (4px radius, hairline), ink "Search" affordance; a mono catalog line ("N skills · content-addressed"); category filters as restrained text/outline controls with the active one marked by a red tick/underline.
- **Masonry:** CSS multi-column, strict 24px gutters, hairline-bordered cards, flush-left content, variable height from content length. No shadows.
- Reduced-motion respected; visible keyboard focus; responsive to mobile (columns collapse).
- Tests via `cd backend && uv run --python 3.12 pytest`. Frontend checks: `npx tsc -b` + `npm run build` + `npx eslint`.

---

## Task 1: Demo seed + dev-DB cleanup + broaden search (backend)

**Files:**
- Create: `backend/app/db/seed_marketplace.py` — `seed_marketplace_demo(db)` inserts ~10 varied demo listings + a v1 `SkillVersion` (real markdown content incl. a mermaid block on 1–2) when the public catalog has < 3 real listings. Idempotent (skip if a demo marker listing already exists).
- Create: `backend/scripts/clean_test_listings.py` — deletes listings whose `source_workspace_id LIKE 'ws\_%'` (the test convention) or `= 'mp_src'`; cascade removes their `skill_versions`. Prints counts.
- Modify: `backend/app/repositories/marketplace_repo.py` — `list()` `q` filter now matches title OR summary OR any tag (currently title only).
- Modify: wire `seed_marketplace_demo` into the existing startup/seed path (see `app/db/seed.py` and how it's invoked in `app/main.py` lifespan) so a fresh DB gets demo content.

**Demo skills (varied categories/lengths for masonry):** CSV → Knowledge Graph (Transformation, featured, mermaid), Entity Resolver (Enrichment), Schema Guardrail (Validation), PII Redactor (Prompt), Address Normalizer (Transformation), Anomaly Detector (Validation), Geocoder (Enrichment), Currency Converter (Transformation), Data Cleanup Suite (Toolkit, featured), Date Parser (Extraction). Each: realistic summary (varied length), 2–3 tags, an author handle, type/category.

- [ ] Step 1 (TDD): write `backend/tests/integration/test_marketplace_seed.py` asserting `seed_marketplace_demo` is idempotent (running twice yields the same count, ≥ 10 listings, each with a v1 version + non-empty content) and that `repo.list(q=...)` matches on summary and tag, not just title. Clean up its own rows in teardown.
- [ ] Step 2: run it (RED).
- [ ] Step 3: implement seed + search broadening.
- [ ] Step 4: run it (GREEN) + full integration suite.
- [ ] Step 5: run the cleanup script against the dev DB and then the seed: `cd backend && uv run --python 3.12 python scripts/clean_test_listings.py && uv run --python 3.12 python -c "import asyncio; from app.db.session import SessionLocal; from app.db.seed_marketplace import seed_marketplace_demo; asyncio.run((lambda: (lambda s: s)(0))())"` — (the implementer will write a tiny runner; the point is: dev DB ends with 0 `ws_*` test rows and ≥10 demo listings). Capture before/after counts.
- [ ] Step 6: commit (seed, script, repo change, seed wiring, test).

## Task 2: Harden the polluting integration test(s) (backend)

**Files:**
- Modify: `backend/tests/integration/test_skill_versioning.py` (and any other test that publishes into a `ws_*` workspace) to delete the listings/versions it created in teardown (or wrap the session in a rollback). Also ensure any on-disk workspace bundle it creates goes to a temp dir or is removed.
- Consider: a shared autouse fixture in `backend/tests/conftest.py` that records and deletes `marketplace_listings` rows created during a test, if that's cleaner than per-test teardown.

- [ ] Step 1: reproduce — note that running `test_skill_versioning.py` twice currently leaves 2 extra rows.
- [ ] Step 2: add teardown/rollback so running the test N times leaves 0 net new rows.
- [ ] Step 3: verify by running the test twice and checking the listing count is unchanged; run full integration suite.
- [ ] Step 4: commit.

## Task 3: Storefront style module + SkillCard (Swiss) (frontend)

**Files:**
- Create: `frontend/src/features/marketplace/storefront.ts` — the Swiss style constants derived from the Global Constraints (radii=4, type scale, gutter=24, swatch size=8, hairline helpers) so cards/home/detail share one source. Reuse `tokens` + `TYPE_ACCENT`.
- Rewrite: `frontend/src/features/marketplace/components/SkillCard.tsx` to the Swiss spec: hairline border (no shadow), 4px radius; top row = 8px category swatch + uppercase mono category label, right-aligned mono type code; grotesque title (Inter 600, -0.02em, NO serif); body summary (variable length → variable height); ≤3 tag chips (text, hairline); hairline divider; footer = flat `@author` + mono `sha <7>` (omit if null) + mono uses count; the ink-black behavior preserved; whole card is a `Link` to `/marketplace/${id}`; hover darkens border to `lineStrong`, no shadow.

- [ ] Step 1: add `storefront.ts`.
- [ ] Step 2: rewrite SkillCard to Swiss; `npx tsc -b` + eslint clean.
- [ ] Step 3: commit.

## Task 4: MarketplacePage — hero + masonry (Swiss) (frontend)

**Files:**
- Rewrite: `frontend/src/features/marketplace/pages/MarketplacePage.tsx`:
  - **Hero** (centered): tight grotesque "Find a data skill"; a mono sub-line "{count} skills · content-addressed"; a centered 560px hairline search input (4px) bound to the existing debounced `q` → `usePublicMarketplace`; category filters from `usePublicCategories` as restrained controls, active marked by a red tick (no pill fills).
  - **Masonry:** CSS `column-count` responsive (4 → 3 → 2 → 1 at breakpoints), 24px `column-gap`, `SkillCard`s with `break-inside: avoid`. Skeleton loading; quiet empty state ("No skills match \"{q}\".").
  - Remove the old CategoryStrip usage if it no longer fits (fold category filters into the hero). Keep PublicLayout's top bar (it already provides wordmark/⌘K) — but since the hero now centers search, ensure no jarring duplicate: keep PublicLayout's slim bar, the hero is the page's own search.

- [ ] Step 1: rewrite the page.
- [ ] Step 2: `npx tsc -b` + `npm run build` + eslint clean.
- [ ] Step 3: commit.

## Task 5: Detail page header — Swiss (frontend)

**Files:**
- Modify: `frontend/src/features/marketplace/pages/MarketplaceDetailPage.tsx` — restyle the HEADER to match (grotesque title -0.02em no serif, uppercase mono category + swatch, prominent mono `sha256:` chip, hairline rules, no shadows). Keep all existing behavior (version selector, login-gated Use skill, curl snippet, versions list, MarkdownPreview). Body/README rendering unchanged.

- [ ] Step 1: restyle header only (don't touch the working logic).
- [ ] Step 2: `npx tsc -b` + eslint clean.
- [ ] Step 3: commit.

## Task 6: Visual verification (controller)

- Run backend + frontend; screenshot the home and a detail page (Chrome DevTools MCP). Critique against the Swiss system (alignment, type scale, red-only-accent, no shadows, masonry rhythm). File any fixes as a follow-up fix pass. Confirm no duplicate skills render.

## Definition of Done
- Dev DB: 0 `ws_*` test listings; ≥10 varied demo skills; running the versioning test twice adds 0 net rows.
- Backend suite green; frontend `tsc -b` + `npm run build` clean.
- Home renders hero + masonry (Swiss), detail header matches; screenshots reviewed; no duplicate skills.
