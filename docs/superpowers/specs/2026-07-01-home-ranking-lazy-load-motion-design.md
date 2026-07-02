# Home Ranking, Lazy Loading & Motion Library — Design Spec

**Date:** 2026-07-01
**Branch:** `feat/home-ranking-lazy-load` (to be created off `main`)
**Status:** Approved (pending spec review) — ready for implementation planning
**Builds on:** the public marketplace (`MarketplacePage`, `usePublicMarketplace`,
`MarketplaceRepository.list`, `MarketplaceService.public_list`, the `/public/marketplace`
route) and the existing `features/shared/fancy` primitives (`NumberTicker`, `SaveFlash`).
**Roadmap position:** Workstream **C** of the six-part marketplace build
(A rich editor ✓ → B per-skill stats/clone ✓ → **C home ranking + lazy load + motion** →
D OTel/Grafana → E framework adapters → F design studio).

## 1. Summary

Turn the marketplace home (`/`, `MarketplacePage`) into a scale-ready, motion-rich
storefront:

1. A **fixed "Top ranked" leaderboard** (top 8 skills by cumulative uses) pinned above
   the results grid. It is a stable global "best of" — it **hides** the moment the user
   searches or applies any facet/category filter, so filtering shows only the results grid.
2. **Infinite / lazy loading** of the results grid as the user scrolls, replacing the
   single 60-item shot. Requires real offset pagination on the backend (and one
   correctness fix: category filtering must move into the SQL query so pagination is sound).
3. A small **motion component library** under `features/shared/fancy` — scroll-reveal,
   staggered card entrance, magnetic buttons, animated gradient headline, a trending-tag
   marquee, cursor-spotlight cards, and shimmer skeletons. **No new dependencies**
   (native IntersectionObserver + CSS + `requestAnimationFrame`, matching the house
   style), and **every effect degrades to static under `prefers-reduced-motion`**.

## 2. Decisions (locked with user)

- **Top ranking:** fixed global leaderboard (top 8 by uses), **hidden while the user is
  searching or filtering**.
- **Motion:** "playful" set — scroll-reveal + stagger + hover-lift, magnetic buttons,
  animated gradient hero text, trending-tag marquee, cursor-spotlight cards, shimmer
  skeletons. No new deps; `prefers-reduced-motion` honored throughout.
- **Pagination:** offset-based (the repo already takes `limit`; add `offset`).
  `hasMore` is inferred from `page.length === pageSize` — no total-count field added.

## 3. Backend

### 3.1 Correctness fix — push category filter into SQL
Today `MarketplaceService.public_list` post-filters category in Python **after** the repo
applies `limit`. With pagination that silently drops/duplicates rows. Fix: add a
`category` parameter to `MarketplaceRepository.list` and filter in SQL with
`func.coalesce(MarketplaceListing.category, MarketplaceListing.type) == category`, then
delete the Python post-filter from the service.

### 3.2 Offset pagination + deterministic order
`MarketplaceRepository.list(..., limit=60, offset=0)`:
- Add `offset: int = 0`; apply `.offset(offset).limit(limit)`.
- Add a **stable secondary sort** so paging can't skip/repeat on ties: every sort branch
  ends `.order_by(<primary> , MarketplaceListing.id)` (e.g. `desc(downloads), id`).
  Sort branches unchanged otherwise: `uses`→`downloads desc`, `recent`→`updated_at desc`,
  `newest`→`created_at desc`.

### 3.3 Service + endpoint pass-through
- `MarketplaceService.public_list(..., limit=60, offset=0, category=None)`: forward
  `category`, `limit`, `offset` to `repo.list`; remove the Python category post-filter.
- `GET /public/marketplace` (in `public.py`): add query params `limit: int = 60` and
  `offset: int = 0` (pass through). Clamp `limit` to `1..60` and `offset >= 0` in the
  route to bound cost. Response stays a bare list of listing dicts (unchanged shape) —
  the client infers `hasMore` from page length.

No schema/migration changes. No new endpoint: the leaderboard reuses this route with
`sort=uses&limit=8&offset=0` and no query/filters.

## 4. Frontend — data layer (`features/marketplace/api/publicMarketplaceApi.ts`)

- **`useInfiniteMarketplace(params, pageSize = 24)`** — `useInfiniteQuery` over
  `/public/marketplace`, sending `limit=pageSize` and `offset=pageParam`. `params` is
  `{ q, type, category, sort, capability, source }`. `getNextPageParam(lastPage, allPages)`
  returns `allPages.length * pageSize` when `lastPage.length === pageSize`, else
  `undefined`. Query key includes all params so filter/search/sort changes refetch fresh.
- **`useTopRanked(limit = 8)`** — plain `useQuery` hitting the same route with
  `sort=uses&limit=8&offset=0` and no filters; returns `PublicListing[]`. Separate key
  (`["public-marketplace-top", limit]`) so it is not disturbed by grid filtering.
- Keep existing `usePublicMarketplace` for any other caller, but `MarketplacePage`
  switches to `useInfiniteMarketplace`.

## 5. Frontend — motion library (`features/shared/fancy/`)

All components: no new deps; disable motion (render final/static state) when
`prefers-reduced-motion: reduce`. Each ships a Vitest test.

- **`usePrefersReducedMotion()`** — `matchMedia("(prefers-reduced-motion: reduce)")`
  hook (SSR-safe; returns `false` when `matchMedia` is absent).
- **`useInView(options?)`** — returns `[ref, inView]` via `IntersectionObserver`
  (once-only by default; `rootMargin`/`threshold` overridable). Falls back to
  `inView = true` immediately when `IntersectionObserver` is undefined (jsdom/SSR).
- **`Reveal({ children, delay = 0, y = 12 })`** — wraps content; when it enters view it
  transitions `opacity 0→1` and `translateY(y)→0` over ~420ms, after `delay` ms (used for
  card stagger). Reduced-motion → renders visible immediately, no transform.
- **`Magnetic({ children, strength = 0.3 })`** — wrapper that translates its child toward
  the cursor on `pointermove` within its bounds and springs back on leave (rAF-eased).
  Reduced-motion → passthrough, no transform. Used on the hero CTA / primary buttons.
- **`GradientText({ children })`** — headline with an animated gradient
  (`background-clip: text`, CSS keyframes). Reduced-motion → solid `tokens.color.ink`,
  no animation.
- **`Marquee({ children, speed = 40, pauseOnHover = true })`** — seamless horizontal
  scroll (duplicates its track; CSS `@keyframes` translateX). Reduced-motion → static,
  horizontally scrollable row.
- **`Spotlight({ children })`** — wrapper that tracks the cursor via a CSS custom property
  (`--mx/--my`) and paints a soft radial highlight over the child on hover. Reduced-motion
  → no highlight. Used to wrap `SkillCard`.
- **`Shimmer({ height, width, radius })`** — animated skeleton block (moving gradient).
  Reduced-motion → flat neutral block. Replaces the plain loading placeholders.

Global CSS keyframes (marquee, gradient, shimmer) live in one small
`features/shared/fancy/fancy.css` imported by those components.

## 6. Frontend — home composition (`features/marketplace`)

- **`components/TopRankedBoard.tsx`** — consumes `useTopRanked(8)`; renders a numbered
  leaderboard: rank numeral, category swatch, title (links to `/marketplace/:id`),
  a mini proportional bar (share of the #1 skill's uses), and an animated use count via
  `NumberTicker`. Rows appear with staggered `Reveal`. Loading → 8 `Shimmer` rows;
  empty → render nothing (board is suppressed).
- **`components/TrendingMarquee.tsx`** — a `Marquee` ribbon of trending category/tag
  chips derived from `usePublicCategories()` (top categories by count). Clicking a chip
  sets the category filter. Sits under the hero.
- **`components/InfiniteSkillGrid.tsx`** — owns the `useInfiniteMarketplace` result:
  flattens pages into the existing masonry grid, wraps each `SkillCard` in
  `Spotlight` + `Reveal` (stagger by index within a page), renders a bottom **sentinel**
  (`useInView`) that calls `fetchNextPage` when visible and `hasNextPage`, shows a small
  `Shimmer` row while `isFetchingNextPage`, and an "end of results" hairline when done.
- **`pages/MarketplacePage.tsx`**:
  - Hero headline uses `GradientText`; the primary search/CTA affordance gets `Magnetic`.
  - `TrendingMarquee` under the hero.
  - `TopRankedBoard` rendered **only when** `isBrowsingDefault` = no `q` **and** no
    `category`/`capability`/`source` selected. As soon as any of those is set, the board
    unmounts and only `InfiniteSkillGrid` (now showing filtered results) is visible.
  - Replace the single-shot list with `InfiniteSkillGrid`, passing the current
    `{ q, type, category, sort, capability, source }`.
  - Keep existing search debounce, category/facet filters, and the trending/newest sort
    toggle exactly as-is (they now feed the infinite query's params).

## 7. Testing (TDD; pytest backend, Vitest frontend)

**Backend**
- `repo.list` category filter: seed listings where `category` is null but `type` matches →
  `coalesce(category, type)` still matches; rows outside the category are excluded.
- `repo.list` offset pagination: seed 5 listings, `limit=2 offset=0` vs `offset=2` vs
  `offset=4` return disjoint, order-stable slices (secondary `id` sort → no overlap on
  equal `downloads`).
- endpoint: `GET /public/marketplace?limit=2&offset=2` returns the second page;
  `limit` clamped above 60; negative `offset` treated as 0.

**Frontend**
- `useInView`: with `IntersectionObserver` mocked, flips `inView` true when the mock fires;
  returns `true` immediately when `IntersectionObserver` is undefined.
- `usePrefersReducedMotion`: reads the mocked `matchMedia` result; `false` when absent.
- `Reveal`: renders children; visible immediately under reduced motion.
- `Magnetic`: renders children; no transform under reduced motion (pointer handler no-op).
- `Marquee`: renders its children twice (duplicated track) for the seamless loop.
- `TopRankedBoard`: from a fixture of 3 listings, renders ranked 01/02/03 with titles and
  use counts; renders nothing on empty data; shows shimmer rows while loading.
- `InfiniteSkillGrid`: with a mocked infinite-query result exposing two pages, renders all
  flattened cards; when the sentinel's `useInView` reports visible and `hasNextPage`, it
  calls `fetchNextPage`; renders the end-of-results marker when `hasNextPage` is false.
- `MarketplacePage`: the `TopRankedBoard` is present with empty search and absent once a
  category/search is set (mock the hooks).

## 8. Files touched

**Backend**
- `app/repositories/marketplace_repo.py` — `list(..., category=None, offset=0)` + SQL
  category filter + stable secondary order.
- `app/services/marketplace_service.py` — `public_list(..., offset=0, category=None)`
  pass-through; remove Python category post-filter.
- `app/api/v1/routers/public.py` — `limit`/`offset` query params (clamped) on
  `GET /marketplace`.

**Frontend**
- `features/marketplace/api/publicMarketplaceApi.ts` — `useInfiniteMarketplace`,
  `useTopRanked`.
- `features/shared/fancy/` — `usePrefersReducedMotion.ts`, `useInView.ts`, `Reveal.tsx`,
  `Magnetic.tsx`, `GradientText.tsx`, `Marquee.tsx`, `Spotlight.tsx`, `Shimmer.tsx`,
  `fancy.css` (+ tests).
- `features/marketplace/components/` — `TopRankedBoard.tsx`, `TrendingMarquee.tsx`,
  `InfiniteSkillGrid.tsx` (+ tests).
- `features/marketplace/pages/MarketplacePage.tsx` — hero motion, marquee, conditional
  leaderboard, infinite grid.

## 9. Out of scope (future workstreams)

OTel/Grafana observability (D), framework adapters (E), design studio (F). Server-driven
"featured" curation beyond the existing `featured` flag, per-tag trending analytics, and
virtualized rendering of the grid are deferred unless they become necessary for scale.
