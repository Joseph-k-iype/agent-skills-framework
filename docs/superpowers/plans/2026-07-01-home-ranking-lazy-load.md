# Home Ranking, Lazy Loading & Motion Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each task ends with an independently testable, committable deliverable.

**Spec:** `docs/superpowers/specs/2026-07-01-home-ranking-lazy-load-motion-design.md`
**Branch:** `feat/home-ranking-lazy-load` (create off `main` before Task 1).

**Goal:** Turn the marketplace home (`/`, `MarketplacePage`) into a scale-ready, motion-rich storefront: a fixed **Top-ranked leaderboard** (top 8 by uses, hidden while searching/filtering), **infinite/lazy loading** of the results grid backed by real offset pagination (plus the correctness fix of pushing the category filter into SQL), and a small **motion library** under `features/shared/fancy` (scroll-reveal, stagger, magnetic buttons, animated gradient headline, trending marquee, cursor-spotlight cards, shimmer skeletons) with **no new dependencies** and full `prefers-reduced-motion` degradation.

**Architecture:** Backend gains `offset` + a SQL `category` filter + a stable secondary `id` sort on `MarketplaceRepository.list`, threaded through `MarketplaceService.public_list` and the `GET /public/marketplace` route (clamped `limit`/`offset`). The response shape is unchanged (a bare list of listing dicts) — the client infers `hasMore` from page length. The frontend adds two query hooks (`useInfiniteMarketplace`, `useTopRanked`) beside the existing `usePublicMarketplace`, a set of self-contained fancy primitives (each a pure component/hook using native `IntersectionObserver` + `matchMedia` + `requestAnimationFrame` + CSS keyframes in one `fancy.css`), and three marketplace components (`TopRankedBoard`, `TrendingMarquee`, `InfiniteSkillGrid`) that `MarketplacePage` composes. All motion effects render their final/static state under `prefers-reduced-motion: reduce`.

**Tech Stack:** React 18, TypeScript 5.5, Vite 5, `@tanstack/react-query` ^5.51 (`useInfiniteQuery`), antd 5, `react-router-dom` ^6.26. Testing: Vitest ^2 + `@testing-library/react` ^16 + `@testing-library/jest-dom`, jsdom ^25. Backend: FastAPI, SQLAlchemy async, PostgreSQL; pytest ^8.2 + pytest-asyncio (`asyncio_mode = "auto"`) run via `uv --python 3.12`.

## Global Constraints

- **Version floors:** React 18 / TS 5.5 / Vite 5 / react-query ^5.51 / antd 5 / Vitest ^2 (frontend); Python 3.11+ (backend runs 3.12 in CI-via-uv). Do not bump any floor.
- **No new dependencies** anywhere. Motion uses only native `IntersectionObserver`, `matchMedia`, `requestAnimationFrame`, and CSS `@keyframes`. Pagination uses react-query's built-in `useInfiniteQuery` (already present). No `framer-motion`, no `react-intersection-observer`, no `react-virtual`.
- **Markdown-stays-stored-format:** N/A to this workstream (no authoring surface touched).
- **`prefers-reduced-motion` is mandatory:** every fancy component MUST render its final/static state (no transform, no keyframe animation, pointer handlers become no-ops) when `matchMedia("(prefers-reduced-motion: reduce)")` matches. `usePrefersReducedMotion` returns `false` when `matchMedia` is absent (jsdom/SSR-safe).
- **Swiss-minimal tokens:** import design values from `@/app/theme/tokens` and storefront constants from `@/features/marketplace/storefront`. Tesla Red (`tokens.color.accent` = `#E82127`) is reserved for functional markers only. Category color comes only from `categoryAccentFor` (`@/features/marketplace/theme`). Data values use `tokens.font.mono`. Surfaces are flat: `RADIUS = 4`, 1px hairline (`tokens.color.line`), no shadow. Grid gutter is `GUTTER = 24`.
- **TDD:** every task is write-failing-test → run (fails) → minimal implementation → run (passes) → commit. No implementation before its test.
- **Working directories:** frontend commands run from `frontend/` (`cd frontend` first); backend commands run from `backend/`.
- **Test commands (discovered):**
  - Backend: `cd backend && uv run --python 3.12 --extra dev pytest <path> -q` — system python is 3.9 but the backend needs 3.11+, so `uv --python 3.12` selects a compatible interpreter and `--extra dev` installs `pytest`/`pytest-asyncio`/`pytest-cov` from `[project.optional-dependencies].dev`. Integration tests run against **live** PostgreSQL + FalkorDB and require `make seed` to have created the `admin` user; they self-clean their listings. `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed on individual tests, but existing files set `pytestmark = pytest.mark.asyncio` — match the file you add to).
  - Frontend single file: `cd frontend && npx vitest run <path>`. All: `npm test -- run`. Typecheck: `npx tsc --noEmit`. Build: `npm run build`.
- **Commit** after every task with a scoped message ending in the Co-Authored-By trailer.

## File Structure

**Backend (modified)**
- `backend/app/repositories/marketplace_repo.py` — `list(...)` gains `category: str | None = None` (SQL `coalesce(category, type)` filter), `offset: int = 0` (`.offset(offset)`), and a stable secondary `.order_by(<primary>, MarketplaceListing.id)`. One responsibility: sound, paginated, category-aware listing query.
- `backend/app/services/marketplace_service.py` — `public_list(..., offset=0, category=None)` forwards `category`/`limit`/`offset` to `repo.list`; the Python category post-filter is deleted. One responsibility: pass-through to the repo (no post-filtering).
- `backend/app/api/v1/routers/public.py` — `GET /marketplace` gains `limit: int = 60` and `offset: int = 0` query params, clamped to `1..60` and `>= 0`. One responsibility: bound and forward pagination params.

**Backend (new tests)**
- `backend/tests/integration/test_marketplace_pagination.py` — repo category-coalesce filter + disjoint offset slices; endpoint pagination + clamp.

**Frontend — data layer (modified)**
- `frontend/src/features/marketplace/api/publicMarketplaceApi.ts` — add `useInfiniteMarketplace(params, pageSize?)` and `useTopRanked(limit?)`. One responsibility: query hooks for the paginated grid and the leaderboard.

**Frontend — motion library (new, `frontend/src/features/shared/fancy/`)**
- `usePrefersReducedMotion.ts` — reduced-motion boolean hook. One responsibility: read the media query, SSR-safe.
- `useInView.ts` — `[ref, inView]` once-only IntersectionObserver hook. One responsibility: report first viewport entry.
- `Reveal.tsx` — opacity/translateY entrance on view. One responsibility: staggered scroll-reveal wrapper.
- `Shimmer.tsx` — animated skeleton block. One responsibility: loading placeholder.
- `Magnetic.tsx` — cursor-attraction wrapper. One responsibility: magnetic hover on the wrapped child.
- `GradientText.tsx` — animated gradient headline. One responsibility: hero text.
- `Marquee.tsx` — seamless duplicated-track horizontal scroll. One responsibility: trending ribbon.
- `Spotlight.tsx` — cursor radial highlight via CSS vars. One responsibility: card hover glow.
- `fancy.css` — the three `@keyframes` (shimmer, gradient-pan, marquee). One responsibility: shared keyframes.

**Frontend — home composition (`frontend/src/features/marketplace/`)**
- `components/TopRankedBoard.tsx` (new) — numbered leaderboard from `useTopRanked(8)`. One responsibility: the "best of" board.
- `components/TrendingMarquee.tsx` (new) — category-chip marquee from `usePublicCategories()`. One responsibility: trending ribbon under the hero.
- `components/InfiniteSkillGrid.tsx` (new) — flattens `useInfiniteMarketplace` pages into the masonry grid + sentinel + end marker. One responsibility: the lazy-loading results grid.
- `pages/MarketplacePage.tsx` (modified) — hero `GradientText`, `Magnetic` search wrapper, `TrendingMarquee`, conditional `TopRankedBoard`, and `InfiniteSkillGrid` in place of the single-shot list. One responsibility: home composition + filter state.

**Frontend (new tests)** — one `__tests__/*.test.ts(x)` beside each new hook/component (paths listed per task).

---

### Task 1: Backend — repo `list` category-in-SQL + offset + stable secondary order

**Files:**
- Modify: `backend/app/repositories/marketplace_repo.py`
- Test: `backend/tests/integration/test_marketplace_pagination.py`

**Interfaces:**
- Consumes: `MarketplaceService`/`ConceptService` (to seed), `SessionLocal`.
- Produces (new signature):
  ```python
  async def list(
      self,
      *,
      q: str | None = None,
      type: str | None = None,
      category: str | None = None,
      capability: str | None = None,
      source: str | None = None,
      sort: str = "uses",
      limit: int = 100,
      offset: int = 0,
  ) -> list[MarketplaceListing]: ...
  ```
  Category filter: `func.coalesce(MarketplaceListing.category, MarketplaceListing.type) == category`. Every sort branch ends `.order_by(<primary>, MarketplaceListing.id)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_marketplace_pagination.py
"""Repo-level pagination + SQL category filter (Workstream C).

Seeds published listings directly through the service, then drives
``MarketplaceRepository.list`` to prove:
- ``coalesce(category, type)`` matches when ``category`` is NULL but ``type`` matches.
- offset slices are disjoint and order-stable (secondary ``id`` sort breaks ties).
Integration test: requires live PG + FalkorDB and a seeded ``admin`` user.
"""

from __future__ import annotations

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.repositories.marketplace_repo import MarketplaceRepository
from app.services.concept_service import ConceptService
from app.storage import paths

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def setup(monkeypatch, tmp_path, graph_name):
    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes

    bootstrap_indexes()


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


async def _publish(cs: ConceptService, ws: str, name: str, file: str) -> None:
    await cs.create(
        workspace_id=ws,
        folder_path="",
        name=name,
        type="skill",
        description=f"{name} desc",
        runtime=None,
        tags=[],
        capabilities=[],
        sources=[],
        body=f"# {name}\nbody",
        frontmatter={},
    )
    await cs.publish(workspace_id=ws, path=file, version="1.0.0")


async def test_category_filter_coalesces_null_category_to_type(setup, admin_id):
    """A listing with category=NULL but type='skill' matches category='skill' in SQL."""
    async with SessionLocal() as db:
        cs = ConceptService(db, _user(admin_id))
        await _publish(cs, "pg_cat_a", "PageCat Alpha", "pagecat-alpha.md")
        await db.commit()

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        # category is NULL on freshly published listings; type is "skill".
        rows = await repo.list(category="skill", limit=100)
        titles = [r.title for r in rows]
        assert "PageCat Alpha" in titles, f"coalesce(category,type) should match: {titles}"
        # A category that matches nothing returns nothing for our seed.
        none = await repo.list(category="nonexistent_cat_zzz", limit=100)
        assert all(r.title != "PageCat Alpha" for r in none)


async def test_offset_slices_are_disjoint_and_stable(setup, admin_id):
    """limit=2 across offset 0/2/4 yields disjoint, order-stable slices."""
    async with SessionLocal() as db:
        cs = ConceptService(db, _user(admin_id))
        for i in range(5):
            await _publish(cs, f"pg_pag_{i}", f"PagePag {i}", f"pagepag-{i}.md")
        await db.commit()

    async with SessionLocal() as db:
        repo = MarketplaceRepository(db)
        # Restrict to our seed via category=skill so counts are our 5+ (order stable regardless).
        page0 = await repo.list(sort="uses", limit=2, offset=0)
        page1 = await repo.list(sort="uses", limit=2, offset=2)
        page2 = await repo.list(sort="uses", limit=2, offset=4)
        ids0 = [str(r.id) for r in page0]
        ids1 = [str(r.id) for r in page1]
        ids2 = [str(r.id) for r in page2]
        assert len(ids0) == 2 and len(ids1) == 2 and len(ids2) >= 1
        # No id repeats across the three consecutive pages.
        seen = ids0 + ids1 + ids2
        assert len(seen) == len(set(seen)), f"pages overlap: {seen}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run --python 3.12 --extra dev pytest tests/integration/test_marketplace_pagination.py -q`
Expected: FAIL — `test_offset_slices_are_disjoint_and_stable` overlaps because `list` ignores `offset` (`TypeError: list() got an unexpected keyword argument 'offset'`), and `test_category_filter_coalesces_null_category_to_type` errors on the unknown `category` kwarg.

- [ ] **Step 3: Write the minimal implementation**

Replace the `list` method in `backend/app/repositories/marketplace_repo.py` with:

```python
    async def list(
        self,
        *,
        q: str | None = None,
        type: str | None = None,
        category: str | None = None,
        capability: str | None = None,
        source: str | None = None,
        sort: str = "uses",
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketplaceListing]:
        stmt = select(MarketplaceListing).where(MarketplaceListing.is_public.is_(True))
        if type:
            stmt = stmt.where(MarketplaceListing.type == type)
        if category:
            # Push category into SQL so pagination is sound. A listing with a NULL
            # category falls back to its ``type`` (the same rule the categories
            # facet and SkillCard use), via COALESCE.
            stmt = stmt.where(
                func.coalesce(MarketplaceListing.category, MarketplaceListing.type)
                == category
            )
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
        # Stable secondary sort on ``id`` so offset paging can't skip/repeat rows
        # that tie on the primary key (e.g. equal downloads).
        stmt = (
            stmt.order_by(order, MarketplaceListing.id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.db.scalars(stmt)).all())
```

(Note: the previous secondary `desc(MarketplaceListing.created_at)` is replaced by `MarketplaceListing.id`, which is the stable, unique tiebreaker the spec requires.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run --python 3.12 --extra dev pytest tests/integration/test_marketplace_pagination.py -q`
Expected: PASS (2 passed), or SKIPPED if FalkorDB is unavailable in the environment.

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add backend/app/repositories/marketplace_repo.py backend/tests/integration/test_marketplace_pagination.py && git commit -m "$(cat <<'EOF'
feat(marketplace): repo.list SQL category filter + offset + stable id order

Category now filters via coalesce(category, type) in SQL; add offset for
paging; secondary sort on id so offset slices are disjoint on ties.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend — service pass-through + endpoint clamped `limit`/`offset`

**Files:**
- Modify: `backend/app/services/marketplace_service.py`, `backend/app/api/v1/routers/public.py`
- Test: `backend/tests/integration/test_marketplace_pagination.py` (append endpoint cases)

**Interfaces:**
- Produces (service):
  ```python
  async def public_list(
      self, *, q=None, type=None, category=None,
      capability: str | None = None, source: str | None = None,
      sort="uses", limit=60, offset=0,
  ) -> list[dict]: ...
  ```
  Forwards `category`, `limit`, `offset` to `repo.list`; **no** Python post-filter.
- Produces (route): `GET /marketplace` accepts `limit: int = 60`, `offset: int = 0`, clamps `limit` to `max(1, min(60, limit))` and `offset` to `max(0, offset)`.

- [ ] **Step 1: Write the failing test** (append to `test_marketplace_pagination.py`)

```python
async def test_endpoint_pagination_and_clamp(setup, admin_id):
    """GET /public/marketplace paginates via limit/offset and clamps out-of-range values."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with SessionLocal() as db:
        cs = ConceptService(db, _user(admin_id))
        for i in range(4):
            await _publish(cs, f"pg_ep_{i}", f"PageEp {i}", f"pageep-{i}.md")
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Page size 2, second page.
        r0 = await ac.get("/api/v1/public/marketplace", params={"limit": 2, "offset": 0})
        r1 = await ac.get("/api/v1/public/marketplace", params={"limit": 2, "offset": 2})
        assert r0.status_code == 200 and r1.status_code == 200
        ids0 = [x["id"] for x in r0.json()["data"]]
        ids1 = [x["id"] for x in r1.json()["data"]]
        assert len(ids0) == 2 and len(ids1) == 2
        assert set(ids0).isdisjoint(set(ids1)), "consecutive pages must not overlap"

        # limit above 60 is clamped to <= 60 rows returned.
        big = await ac.get("/api/v1/public/marketplace", params={"limit": 500})
        assert big.status_code == 200
        assert len(big.json()["data"]) <= 60

        # negative offset is treated as 0 (same first row as offset=0).
        neg = await ac.get("/api/v1/public/marketplace", params={"limit": 2, "offset": -5})
        assert neg.status_code == 200
        assert [x["id"] for x in neg.json()["data"]] == ids0
```

(The envelope wraps the list under `data` — see `app.core.envelope.success`; the existing `test_public_marketplace.py` reads `r.json()["data"]` the same way. Confirm the mount prefix `/api/v1/public` matches that file; if it differs, use the prefix that file uses.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run --python 3.12 --extra dev pytest tests/integration/test_marketplace_pagination.py::test_endpoint_pagination_and_clamp -q`
Expected: FAIL — the route ignores `limit`/`offset` (unexpected query params are dropped), so `offset=2` returns the same rows as `offset=0`; the disjoint assertion fails.

- [ ] **Step 3: Write the minimal implementation**

In `backend/app/services/marketplace_service.py`, replace `public_list`:

```python
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
        offset=0,
    ) -> list[dict]:
        rows = await self.repo.list(
            q=q,
            type=type,
            category=category,
            capability=capability,
            source=source,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return [_listing_dict(x) for x in rows]
```

(The `if category: rows = [r for r in rows if (r.category or r.type) == category]` post-filter is deleted — category now filters in SQL before `limit`/`offset`.)

In `backend/app/api/v1/routers/public.py`, replace the `public_list` route:

```python
@router.get("/marketplace")
async def public_list(
    q: str | None = None,
    type: str | None = None,
    category: str | None = None,
    capability: str | None = None,
    source: str | None = None,
    sort: str = "uses",
    limit: int = 60,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    # Clamp to bound query cost: at most 60 rows per page, non-negative offset.
    limit = max(1, min(60, limit))
    offset = max(0, offset)
    svc = MarketplaceService(db, None)
    return success(
        await svc.public_list(
            q=q,
            type=type,
            category=category,
            capability=capability,
            source=source,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run --python 3.12 --extra dev pytest tests/integration/test_marketplace_pagination.py -q`
Expected: PASS (3 passed) or SKIPPED without services. Also run the existing facet suite to confirm no regression from removing the post-filter:
`cd backend && uv run --python 3.12 --extra dev pytest tests/integration/test_marketplace_facets.py tests/integration/test_public_marketplace.py -q` → PASS.

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add backend/app/services/marketplace_service.py backend/app/api/v1/routers/public.py backend/tests/integration/test_marketplace_pagination.py && git commit -m "$(cat <<'EOF'
feat(marketplace): service/endpoint offset+category pass-through, clamped

public_list forwards category/limit/offset to the repo (drops the Python
post-filter); GET /marketplace clamps limit to 1..60 and offset to >=0.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: fancy — `usePrefersReducedMotion` + `useInView` hooks

**Files:**
- Create: `frontend/src/features/shared/fancy/usePrefersReducedMotion.ts`, `frontend/src/features/shared/fancy/useInView.ts`
- Test: `frontend/src/features/shared/fancy/__tests__/usePrefersReducedMotion.test.tsx`, `frontend/src/features/shared/fancy/__tests__/useInView.test.tsx`

**Interfaces:**
- Produces: `usePrefersReducedMotion(): boolean`; `useInView<T extends Element = HTMLDivElement>(options?: { rootMargin?: string; threshold?: number; once?: boolean }): [React.RefObject<T>, boolean]`.
- Consumed by: `Reveal`, `Magnetic`, `GradientText`, `Marquee`, `Spotlight`, `Shimmer` (reduced motion); `InfiniteSkillGrid` sentinel + `Reveal` (in view).

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/features/shared/fancy/__tests__/usePrefersReducedMotion.test.tsx
import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { usePrefersReducedMotion } from "../usePrefersReducedMotion";

const original = window.matchMedia;
afterEach(() => {
  window.matchMedia = original;
  vi.restoreAllMocks();
});

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe("usePrefersReducedMotion", () => {
  it("returns true when the media query matches", () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(true);
  });

  it("returns false when the media query does not match", () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(false);
  });

  it("returns false when matchMedia is unavailable", () => {
    // @ts-expect-error simulate SSR / absent API
    window.matchMedia = undefined;
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(false);
  });
});
```

```tsx
// frontend/src/features/shared/fancy/__tests__/useInView.test.tsx
import { render, screen } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useInView } from "../useInView";

const originalIO = globalThis.IntersectionObserver;
afterEach(() => {
  globalThis.IntersectionObserver = originalIO;
  vi.restoreAllMocks();
});

function Probe() {
  const [ref, inView] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} data-testid="probe">
      {inView ? "in" : "out"}
    </div>
  );
}

describe("useInView", () => {
  it("flips inView to true when the observer reports an intersection", () => {
    let captured: ((entries: { isIntersecting: boolean }[]) => void) | null = null;
    const observe = vi.fn();
    const disconnect = vi.fn();
    globalThis.IntersectionObserver = vi
      .fn()
      .mockImplementation((cb: (entries: { isIntersecting: boolean }[]) => void) => {
        captured = cb;
        return { observe, disconnect, unobserve: vi.fn(), takeRecords: vi.fn() };
      }) as unknown as typeof IntersectionObserver;

    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("out");
    expect(observe).toHaveBeenCalledTimes(1);
    act(() => {
      captured?.([{ isIntersecting: true }]);
    });
    expect(screen.getByTestId("probe")).toHaveTextContent("in");
  });

  it("reports inView=true immediately when IntersectionObserver is undefined", () => {
    // @ts-expect-error simulate jsdom/SSR without IO
    globalThis.IntersectionObserver = undefined;
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("in");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/usePrefersReducedMotion.test.tsx src/features/shared/fancy/__tests__/useInView.test.tsx`
Expected: FAIL — "Failed to resolve import ../usePrefersReducedMotion" / "../useInView".

- [ ] **Step 3: Write the minimal implementations**

```ts
// frontend/src/features/shared/fancy/usePrefersReducedMotion.ts
import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/**
 * True when the user asked the OS to reduce motion. SSR-safe: returns `false`
 * when `matchMedia` is unavailable (jsdom without a shim, or server render).
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia(QUERY).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mql = window.matchMedia(QUERY);
    const onChange = () => setReduced(mql.matches);
    onChange();
    // Older Safari exposes addListener; guard for both.
    if (mql.addEventListener) mql.addEventListener("change", onChange);
    else mql.addListener(onChange);
    return () => {
      if (mql.removeEventListener) mql.removeEventListener("change", onChange);
      else mql.removeListener(onChange);
    };
  }, []);

  return reduced;
}

export default usePrefersReducedMotion;
```

```ts
// frontend/src/features/shared/fancy/useInView.ts
import { useEffect, useRef, useState } from "react";

export interface UseInViewOptions {
  rootMargin?: string;
  threshold?: number;
  /** Stop observing after the first intersection (default true). */
  once?: boolean;
}

/**
 * `[ref, inView]` via IntersectionObserver. Once-only by default. Falls back to
 * `inView = true` immediately when IntersectionObserver is undefined (jsdom/SSR),
 * so content is never permanently hidden.
 */
export function useInView<T extends Element = HTMLDivElement>(
  options: UseInViewOptions = {},
): [React.RefObject<T>, boolean] {
  const { rootMargin = "0px", threshold = 0, once = true } = options;
  const ref = useRef<T>(null);
  const [inView, setInView] = useState<boolean>(
    () => typeof IntersectionObserver === "undefined",
  );

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          setInView(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { rootMargin, threshold },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [rootMargin, threshold, once]);

  return [ref, inView];
}

export default useInView;
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/usePrefersReducedMotion.test.tsx src/features/shared/fancy/__tests__/useInView.test.tsx`
Expected: PASS (3 + 2 = 5 tests).

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/shared/fancy/usePrefersReducedMotion.ts frontend/src/features/shared/fancy/useInView.ts frontend/src/features/shared/fancy/__tests__/usePrefersReducedMotion.test.tsx frontend/src/features/shared/fancy/__tests__/useInView.test.tsx && git commit -m "$(cat <<'EOF'
feat(fancy): usePrefersReducedMotion + useInView hooks

Native matchMedia + IntersectionObserver, SSR/jsdom-safe fallbacks.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: fancy — `Reveal` + `Shimmer` (+ `fancy.css` keyframes)

**Files:**
- Create: `frontend/src/features/shared/fancy/fancy.css`, `frontend/src/features/shared/fancy/Reveal.tsx`, `frontend/src/features/shared/fancy/Shimmer.tsx`
- Test: `frontend/src/features/shared/fancy/__tests__/Reveal.test.tsx`, `frontend/src/features/shared/fancy/__tests__/Shimmer.test.tsx`

**Interfaces:**
- Produces: `Reveal({ children, delay?, y? }: { children: React.ReactNode; delay?: number; y?: number })`; `Shimmer({ height, width, radius }: { height: number | string; width?: number | string; radius?: number })`.
- Consumes: `usePrefersReducedMotion`, `useInView`, `fancy.css`, `tokens`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/features/shared/fancy/__tests__/Reveal.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => true),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Reveal } from "../Reveal";

describe("Reveal", () => {
  it("renders its children", () => {
    render(<Reveal>hello reveal</Reveal>);
    expect(screen.getByText("hello reveal")).toBeInTheDocument();
  });

  it("renders visible (opacity 1, no transform) under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Reveal>
        <span data-testid="kid">x</span>
      </Reveal>,
    );
    const wrapper = screen.getByTestId("kid").parentElement as HTMLElement;
    expect(wrapper.style.opacity).toBe("1");
    expect(wrapper.style.transform).toBe("none");
  });
});
```

```tsx
// frontend/src/features/shared/fancy/__tests__/Shimmer.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Shimmer } from "../Shimmer";

describe("Shimmer", () => {
  it("renders a block with the requested height and role presentation", () => {
    render(<Shimmer height={40} width={120} />);
    const block = screen.getByRole("presentation");
    expect(block.style.height).toBe("40px");
    expect(block.style.width).toBe("120px");
  });

  it("applies the animated class when motion is allowed and drops it under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(false);
    const { rerender } = render(<Shimmer height={10} />);
    expect(screen.getByRole("presentation").className).toContain("fancy-shimmer");
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    rerender(<Shimmer height={10} />);
    expect(screen.getByRole("presentation").className).not.toContain("fancy-shimmer");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/Reveal.test.tsx src/features/shared/fancy/__tests__/Shimmer.test.tsx`
Expected: FAIL — "Failed to resolve import ../Reveal" / "../Shimmer".

- [ ] **Step 3: Write the minimal implementations**

```css
/* frontend/src/features/shared/fancy/fancy.css */
/* Shared keyframes for the fancy motion library. Consumers gate these behind
   prefers-reduced-motion in JS (they only attach the animating class when
   motion is allowed), so no @media guard is strictly required here — but we
   keep one as defense-in-depth for the global no-JS case. */

@keyframes fancy-shimmer-pan {
  0% { background-position: -150% 0; }
  100% { background-position: 150% 0; }
}

@keyframes fancy-gradient-pan {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

@keyframes fancy-marquee-scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.fancy-shimmer {
  background-size: 200% 100%;
  animation: fancy-shimmer-pan 1.4s ease-in-out infinite;
}

.fancy-gradient {
  background-size: 200% 200%;
  animation: fancy-gradient-pan 6s ease infinite;
}

.fancy-marquee-track {
  animation: fancy-marquee-scroll linear infinite;
}

.fancy-marquee--paused:hover .fancy-marquee-track {
  animation-play-state: paused;
}

@media (prefers-reduced-motion: reduce) {
  .fancy-shimmer,
  .fancy-gradient,
  .fancy-marquee-track {
    animation: none !important;
  }
}
```

```tsx
// frontend/src/features/shared/fancy/Reveal.tsx
import { useEffect, useState, type ReactNode } from "react";
import { useInView } from "./useInView";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Reveals `children` when they scroll into view: opacity 0→1 and
 * translateY(y)→0 over ~420ms, after `delay` ms (used for card stagger).
 * Reduced motion → visible immediately, no transform.
 */
export function Reveal({
  children,
  delay = 0,
  y = 12,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
}) {
  const reduced = usePrefersReducedMotion();
  const [ref, inView] = useInView<HTMLDivElement>();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!inView) return;
    if (delay <= 0) {
      setShown(true);
      return;
    }
    const t = setTimeout(() => setShown(true), delay);
    return () => clearTimeout(t);
  }, [inView, delay]);

  const visible = reduced || shown;

  return (
    <div
      ref={ref}
      style={{
        opacity: reduced ? 1 : visible ? 1 : 0,
        transform: reduced ? "none" : visible ? "translateY(0)" : `translateY(${y}px)`,
        transition: reduced ? "none" : "opacity 420ms ease, transform 420ms ease",
        willChange: reduced ? undefined : "opacity, transform",
      }}
    >
      {children}
    </div>
  );
}

export default Reveal;
```

```tsx
// frontend/src/features/shared/fancy/Shimmer.tsx
import { tokens } from "@/app/theme/tokens";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Animated skeleton block (moving gradient). Reduced motion → flat neutral
 * block. Used as the loading placeholder for the leaderboard and grid tail.
 */
export function Shimmer({
  height,
  width = "100%",
  radius = 4,
}: {
  height: number | string;
  width?: number | string;
  radius?: number;
}) {
  const reduced = usePrefersReducedMotion();
  return (
    <div
      role="presentation"
      className={reduced ? undefined : "fancy-shimmer"}
      style={{
        height: typeof height === "number" ? `${height}px` : height,
        width: typeof width === "number" ? `${width}px` : width,
        borderRadius: radius,
        background: reduced
          ? tokens.color.line
          : `linear-gradient(90deg, ${tokens.color.line} 0%, ${tokens.color.canvas} 50%, ${tokens.color.line} 100%)`,
      }}
    />
  );
}

export default Shimmer;
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/Reveal.test.tsx src/features/shared/fancy/__tests__/Shimmer.test.tsx`
Expected: PASS (2 + 2 = 4 tests). (`vitest.config.ts` sets `css: false`, so the `import "./fancy.css"` is a no-op in tests and does not need mocking.)

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/shared/fancy/fancy.css frontend/src/features/shared/fancy/Reveal.tsx frontend/src/features/shared/fancy/Shimmer.tsx frontend/src/features/shared/fancy/__tests__/Reveal.test.tsx frontend/src/features/shared/fancy/__tests__/Shimmer.test.tsx && git commit -m "$(cat <<'EOF'
feat(fancy): Reveal + Shimmer with shared fancy.css keyframes

Scroll-reveal wrapper and animated skeleton; both static under reduced motion.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: fancy — `Magnetic` + `GradientText`

**Files:**
- Create: `frontend/src/features/shared/fancy/Magnetic.tsx`, `frontend/src/features/shared/fancy/GradientText.tsx`
- Test: `frontend/src/features/shared/fancy/__tests__/Magnetic.test.tsx`, `frontend/src/features/shared/fancy/__tests__/GradientText.test.tsx`

**Interfaces:**
- Produces: `Magnetic({ children, strength? }: { children: React.ReactNode; strength?: number })`; `GradientText({ children }: { children: React.ReactNode })`.
- Consumes: `usePrefersReducedMotion`, `fancy.css`, `tokens`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/features/shared/fancy/__tests__/Magnetic.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Magnetic } from "../Magnetic";

describe("Magnetic", () => {
  it("renders its children", () => {
    render(
      <Magnetic>
        <button type="button">Go</button>
      </Magnetic>,
    );
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });

  it("does not transform under reduced motion (pointer handler is a no-op)", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Magnetic>
        <span data-testid="kid">x</span>
      </Magnetic>,
    );
    const wrap = screen.getByTestId("kid").parentElement as HTMLElement;
    fireEvent.pointerMove(wrap, { clientX: 50, clientY: 50 });
    expect(wrap.style.transform === "" || wrap.style.transform === "none").toBe(true);
  });
});
```

```tsx
// frontend/src/features/shared/fancy/__tests__/GradientText.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { GradientText } from "../GradientText";

describe("GradientText", () => {
  it("renders the headline text", () => {
    render(<GradientText>Find a data skill</GradientText>);
    expect(screen.getByText("Find a data skill")).toBeInTheDocument();
  });

  it("uses the animated gradient class when motion is allowed", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(false);
    render(<GradientText>Hi</GradientText>);
    expect(screen.getByText("Hi").className).toContain("fancy-gradient");
  });

  it("renders solid ink (no gradient class) under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(<GradientText>Hi</GradientText>);
    const el = screen.getByText("Hi");
    expect(el.className).not.toContain("fancy-gradient");
    expect(el.style.color).not.toBe("");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/Magnetic.test.tsx src/features/shared/fancy/__tests__/GradientText.test.tsx`
Expected: FAIL — "Failed to resolve import ../Magnetic" / "../GradientText".

- [ ] **Step 3: Write the minimal implementations**

```tsx
// frontend/src/features/shared/fancy/Magnetic.tsx
import { useRef, type ReactNode } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

/**
 * Translates its child toward the cursor within its bounds (rAF-eased) and
 * springs back on leave. Reduced motion → passthrough, no transform.
 */
export function Magnetic({
  children,
  strength = 0.3,
}: {
  children: ReactNode;
  strength?: number;
}) {
  const reduced = usePrefersReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const raf = useRef(0);

  const apply = (x: number, y: number) => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => {
      const el = ref.current;
      if (el) el.style.transform = `translate(${x}px, ${y}px)`;
    });
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduced) return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const dx = (e.clientX - (rect.left + rect.width / 2)) * strength;
    const dy = (e.clientY - (rect.top + rect.height / 2)) * strength;
    apply(dx, dy);
  };

  const onPointerLeave = () => {
    if (reduced) return;
    apply(0, 0);
  };

  return (
    <div
      ref={ref}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      style={{
        display: "inline-block",
        transition: reduced ? undefined : "transform 220ms cubic-bezier(0.22, 1, 0.36, 1)",
        willChange: reduced ? undefined : "transform",
      }}
    >
      {children}
    </div>
  );
}

export default Magnetic;
```

```tsx
// frontend/src/features/shared/fancy/GradientText.tsx
import type { CSSProperties, ReactNode } from "react";
import { tokens } from "@/app/theme/tokens";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Headline with an animated gradient (background-clip: text). Reduced motion →
 * solid `tokens.color.ink`, no animation.
 */
export function GradientText({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  const reduced = usePrefersReducedMotion();
  if (reduced) {
    return <span style={{ color: tokens.color.ink, ...style }}>{children}</span>;
  }
  return (
    <span
      className="fancy-gradient"
      style={{
        backgroundImage: `linear-gradient(90deg, ${tokens.color.ink} 0%, ${tokens.color.accent} 50%, ${tokens.color.ink} 100%)`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        WebkitTextFillColor: "transparent",
        ...style,
      }}
    >
      {children}
    </span>
  );
}

export default GradientText;
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/Magnetic.test.tsx src/features/shared/fancy/__tests__/GradientText.test.tsx`
Expected: PASS (2 + 3 = 5 tests).

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/shared/fancy/Magnetic.tsx frontend/src/features/shared/fancy/GradientText.tsx frontend/src/features/shared/fancy/__tests__/Magnetic.test.tsx frontend/src/features/shared/fancy/__tests__/GradientText.test.tsx && git commit -m "$(cat <<'EOF'
feat(fancy): Magnetic + GradientText

Cursor-attraction wrapper and animated gradient headline; both degrade to
static/solid under reduced motion.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: fancy — `Marquee` + `Spotlight`

**Files:**
- Create: `frontend/src/features/shared/fancy/Marquee.tsx`, `frontend/src/features/shared/fancy/Spotlight.tsx`
- Test: `frontend/src/features/shared/fancy/__tests__/Marquee.test.tsx`, `frontend/src/features/shared/fancy/__tests__/Spotlight.test.tsx`

**Interfaces:**
- Produces: `Marquee({ children, speed?, pauseOnHover? }: { children: React.ReactNode; speed?: number; pauseOnHover?: boolean })`; `Spotlight({ children }: { children: React.ReactNode })`.
- Consumes: `usePrefersReducedMotion`, `fancy.css`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/features/shared/fancy/__tests__/Marquee.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Marquee } from "../Marquee";

describe("Marquee", () => {
  it("duplicates its track so the loop is seamless (children rendered twice)", () => {
    render(
      <Marquee>
        <span>trending-tag</span>
      </Marquee>,
    );
    // One copy in the real track, one in the aria-hidden clone.
    expect(screen.getAllByText("trending-tag")).toHaveLength(2);
  });

  it("renders a static, scrollable row (no animation class) under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Marquee>
        <span>chip</span>
      </Marquee>,
    );
    // Under reduced motion we still duplicate is unnecessary: render once, no track class.
    const tracks = document.querySelectorAll(".fancy-marquee-track");
    expect(tracks).toHaveLength(0);
    expect(screen.getByText("chip")).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/features/shared/fancy/__tests__/Spotlight.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Spotlight } from "../Spotlight";

describe("Spotlight", () => {
  it("renders its children", () => {
    render(
      <Spotlight>
        <div data-testid="card">card</div>
      </Spotlight>,
    );
    expect(screen.getByTestId("card")).toBeInTheDocument();
  });

  it("sets the --mx/--my custom properties on pointer move when motion is allowed", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(false);
    render(
      <Spotlight>
        <div data-testid="card">card</div>
      </Spotlight>,
    );
    const wrap = screen.getByTestId("card").parentElement as HTMLElement;
    fireEvent.pointerMove(wrap, { clientX: 30, clientY: 20 });
    expect(wrap.style.getPropertyValue("--mx")).not.toBe("");
    expect(wrap.style.getPropertyValue("--my")).not.toBe("");
  });

  it("does not set custom properties under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Spotlight>
        <div data-testid="card">card</div>
      </Spotlight>,
    );
    const wrap = screen.getByTestId("card").parentElement as HTMLElement;
    fireEvent.pointerMove(wrap, { clientX: 30, clientY: 20 });
    expect(wrap.style.getPropertyValue("--mx")).toBe("");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/Marquee.test.tsx src/features/shared/fancy/__tests__/Spotlight.test.tsx`
Expected: FAIL — "Failed to resolve import ../Marquee" / "../Spotlight".

- [ ] **Step 3: Write the minimal implementations**

```tsx
// frontend/src/features/shared/fancy/Marquee.tsx
import type { ReactNode } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Seamless horizontal scroll: duplicates its track and animates the pair by
 * -50% via CSS. Reduced motion → a single static, horizontally scrollable row.
 */
export function Marquee({
  children,
  speed = 40,
  pauseOnHover = true,
}: {
  children: ReactNode;
  speed?: number;
  pauseOnHover?: boolean;
}) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return (
      <div style={{ overflowX: "auto", display: "flex", gap: 16, whiteSpace: "nowrap" }}>
        {children}
      </div>
    );
  }

  const trackStyle: React.CSSProperties = {
    display: "flex",
    gap: 16,
    width: "max-content",
    whiteSpace: "nowrap",
    animationDuration: `${speed}s`,
  };

  return (
    <div
      className={`fancy-marquee${pauseOnHover ? " fancy-marquee--paused" : ""}`}
      style={{ overflow: "hidden", display: "flex", width: "100%" }}
    >
      <div className="fancy-marquee-track" style={trackStyle}>
        <div style={{ display: "flex", gap: 16 }}>{children}</div>
        <div style={{ display: "flex", gap: 16 }} aria-hidden>
          {children}
        </div>
      </div>
    </div>
  );
}

export default Marquee;
```

```tsx
// frontend/src/features/shared/fancy/Spotlight.tsx
import type { ReactNode } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import { tokens } from "@/app/theme/tokens";

/**
 * Tracks the cursor via `--mx`/`--my` custom properties and paints a soft radial
 * highlight over the child on hover. Reduced motion → no highlight (passthrough).
 */
export function Spotlight({ children }: { children: ReactNode }) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return <div>{children}</div>;
  }

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    el.style.setProperty("--my", `${e.clientY - rect.top}px`);
  };

  return (
    <div
      onPointerMove={onPointerMove}
      style={{
        position: "relative",
        borderRadius: 4,
        // Soft radial highlight anchored at the cursor; transparent until hovered.
        backgroundImage: `radial-gradient(180px circle at var(--mx, 50%) var(--my, 50%), ${tokens.color.line} 0%, transparent 60%)`,
      }}
    >
      {children}
    </div>
  );
}

export default Spotlight;
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/Marquee.test.tsx src/features/shared/fancy/__tests__/Spotlight.test.tsx`
Expected: PASS (2 + 3 = 5 tests).

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/shared/fancy/Marquee.tsx frontend/src/features/shared/fancy/Spotlight.tsx frontend/src/features/shared/fancy/__tests__/Marquee.test.tsx frontend/src/features/shared/fancy/__tests__/Spotlight.test.tsx && git commit -m "$(cat <<'EOF'
feat(fancy): Marquee + Spotlight

Seamless duplicated-track ribbon and cursor-tracked radial highlight; both
degrade to static under reduced motion.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: api — `useInfiniteMarketplace` + `useTopRanked`

**Files:**
- Modify: `frontend/src/features/marketplace/api/publicMarketplaceApi.ts`
- Test: `frontend/src/features/marketplace/api/__tests__/publicMarketplaceApi.test.tsx`

**Interfaces:**
- Consumes: `http`, `unwrap` from `@/shared/api/client`; `useInfiniteQuery`, `useQuery` from `@tanstack/react-query`; `PublicListing`.
- Produces:
  ```ts
  export interface InfiniteParams {
    q?: string; type?: string; category?: string;
    sort: SortKey; capability?: string; source?: string;
  }
  export function useInfiniteMarketplace(params: InfiniteParams, pageSize?: number): UseInfiniteQueryResult<InfiniteData<PublicListing[]>, Error>;
  export function useTopRanked(limit?: number): UseQueryResult<PublicListing[], Error>;
  ```
  `getNextPageParam(lastPage, allPages)` → `allPages.length * pageSize` when `lastPage.length === pageSize`, else `undefined`. `useTopRanked` key: `["public-marketplace-top", limit]`, request `sort=uses&limit&offset=0`, no filters.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/marketplace/api/__tests__/publicMarketplaceApi.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/shared/api/client", () => ({
  http: { get: vi.fn() },
  unwrap: (p: Promise<{ data: { data: unknown } }>) => p.then((r) => r.data.data),
}));

import { http } from "@/shared/api/client";
import { useInfiniteMarketplace, useTopRanked } from "../publicMarketplaceApi";

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const listing = (id: string) => ({
  id,
  title: `T${id}`,
  featured: false,
  version: "1",
  tags: [],
  downloads: 0,
});

afterEach(() => vi.clearAllMocks());

describe("useInfiniteMarketplace", () => {
  it("requests limit=pageSize & offset=0 on the first page and exposes hasNextPage when full", async () => {
    const page = Array.from({ length: 3 }, (_, i) => listing(`a${i}`));
    vi.mocked(http.get).mockResolvedValue({ data: { data: page } });

    const { result } = renderHook(() => useInfiniteMarketplace({ sort: "uses" }, 3), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // First call used offset 0 and limit 3.
    expect(http.get).toHaveBeenCalledWith(
      "/public/marketplace",
      expect.objectContaining({ params: expect.objectContaining({ limit: 3, offset: 0, sort: "uses" }) }),
    );
    // A full page (=== pageSize) means there is a next page.
    expect(result.current.hasNextPage).toBe(true);
  });

  it("stops paginating when a short page comes back", async () => {
    vi.mocked(http.get).mockResolvedValue({ data: { data: [listing("only")] } });
    const { result } = renderHook(() => useInfiniteMarketplace({ sort: "uses" }, 3), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.hasNextPage).toBe(false);
  });
});

describe("useTopRanked", () => {
  it("requests sort=uses with the given limit and no filters", async () => {
    const top = [listing("top1"), listing("top2")];
    vi.mocked(http.get).mockResolvedValue({ data: { data: top } });
    const { result } = renderHook(() => useTopRanked(8), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith(
      "/public/marketplace",
      { params: { sort: "uses", limit: 8, offset: 0 } },
    );
    expect(result.current.data).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/marketplace/api/__tests__/publicMarketplaceApi.test.tsx`
Expected: FAIL — `useInfiniteMarketplace`/`useTopRanked` are not exported from `../publicMarketplaceApi`.

- [ ] **Step 3: Write the minimal implementation** (append to `publicMarketplaceApi.ts`)

Change the top import line from:
```ts
import { useQuery } from "@tanstack/react-query";
```
to:
```ts
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
```

Then append at the end of the file:

```ts
export interface InfiniteParams {
  q?: string;
  type?: string;
  category?: string;
  sort: SortKey;
  capability?: string;
  source?: string;
}

/**
 * Infinite/lazy grid over /public/marketplace. Sends `limit=pageSize` and
 * `offset=pageParam`; `hasMore` is inferred from `lastPage.length === pageSize`
 * (no total-count field). The query key includes every param so a filter,
 * search, or sort change refetches from page 0.
 */
export function useInfiniteMarketplace(params: InfiniteParams, pageSize = 24) {
  return useInfiniteQuery({
    queryKey: [
      "public-marketplace-infinite",
      params.q ?? "",
      params.type ?? "",
      params.category ?? "",
      params.sort,
      params.capability ?? "",
      params.source ?? "",
      pageSize,
    ],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap<PublicListing[]>(
        http.get(`/public/marketplace`, {
          params: {
            q: params.q || undefined,
            type: params.type || undefined,
            category: params.category || undefined,
            sort: params.sort,
            capability: params.capability || undefined,
            source: params.source || undefined,
            limit: pageSize,
            offset: pageParam,
          },
        }),
      ),
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length === pageSize ? allPages.length * pageSize : undefined,
  });
}

/**
 * The fixed "Top ranked" leaderboard: same route, `sort=uses`, no filters, its
 * own query key so grid filtering never disturbs it.
 */
export function useTopRanked(limit = 8) {
  return useQuery({
    queryKey: ["public-marketplace-top", limit],
    queryFn: () =>
      unwrap<PublicListing[]>(
        http.get(`/public/marketplace`, {
          params: { sort: "uses", limit, offset: 0 },
        }),
      ),
  });
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/marketplace/api/__tests__/publicMarketplaceApi.test.tsx`
Expected: PASS (3 tests). Then `cd frontend && npx tsc --noEmit` → clean.

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/marketplace/api/publicMarketplaceApi.ts frontend/src/features/marketplace/api/__tests__/publicMarketplaceApi.test.tsx && git commit -m "$(cat <<'EOF'
feat(fe): useInfiniteMarketplace + useTopRanked hooks

Offset-paginated infinite grid (hasMore from page length) and a separate
top-ranked leaderboard query.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: marketplace — `TopRankedBoard` component

**Files:**
- Create: `frontend/src/features/marketplace/components/TopRankedBoard.tsx`
- Test: `frontend/src/features/marketplace/components/__tests__/TopRankedBoard.test.tsx`

**Interfaces:**
- Consumes: `useTopRanked` (mocked in test), `NumberTicker`, `Reveal`, `Shimmer`, `categoryAccentFor`, `swatchStyle`, `storefrontType`, `tokens`, `Link`.
- Produces: `TopRankedBoard(): JSX.Element | null` (renders `null` on empty data).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/marketplace/components/__tests__/TopRankedBoard.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  Link: ({ children, to }: { children?: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("../../api/publicMarketplaceApi", () => ({ useTopRanked: vi.fn() }));
// NumberTicker animates via rAF; render its value directly for a stable assert.
vi.mock("@/features/shared/fancy/NumberTicker", () => ({
  NumberTicker: ({ value }: { value: number }) => <span>{value}</span>,
}));
vi.mock("@/features/shared/fancy/Reveal", () => ({
  Reveal: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/shared/fancy/Shimmer", () => ({
  Shimmer: () => <div data-testid="shimmer" />,
}));

import { useTopRanked } from "../../api/publicMarketplaceApi";
import { TopRankedBoard } from "../TopRankedBoard";

const listing = (id: string, title: string, downloads: number) => ({
  id,
  title,
  featured: false,
  version: "1",
  tags: [],
  downloads,
  category: "extraction",
  type: "skill",
});

describe("TopRankedBoard", () => {
  it("renders ranked rows 01/02/03 with titles and use counts", () => {
    vi.mocked(useTopRanked).mockReturnValue({
      data: [listing("a", "Alpha", 300), listing("b", "Beta", 150), listing("c", "Gamma", 30)],
      isLoading: false,
    } as unknown as ReturnType<typeof useTopRanked>);

    render(<TopRankedBoard />);
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("300")).toBeInTheDocument();
    // Title links to the detail route.
    expect(screen.getByText("Alpha").closest("a")).toHaveAttribute("href", "/marketplace/a");
  });

  it("renders nothing when the leaderboard is empty", () => {
    vi.mocked(useTopRanked).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useTopRanked>);
    const { container } = render(<TopRankedBoard />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows shimmer rows while loading", () => {
    vi.mocked(useTopRanked).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof useTopRanked>);
    render(<TopRankedBoard />);
    expect(screen.getAllByTestId("shimmer").length).toBe(8);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/marketplace/components/__tests__/TopRankedBoard.test.tsx`
Expected: FAIL — "Failed to resolve import ../TopRankedBoard".

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/features/marketplace/components/TopRankedBoard.tsx
import { Link } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { NumberTicker } from "@/features/shared/fancy/NumberTicker";
import { Reveal } from "@/features/shared/fancy/Reveal";
import { Shimmer } from "@/features/shared/fancy/Shimmer";
import { categoryAccentFor } from "@/features/marketplace/theme";
import { RADIUS, storefrontType, swatchStyle } from "@/features/marketplace/storefront";
import { useTopRanked } from "../api/publicMarketplaceApi";

/**
 * Fixed "Top ranked" leaderboard — top 8 skills by cumulative uses. A stable
 * global "best of": rank numeral, category swatch, title, a proportional mini
 * bar (share of the #1 skill's uses), and an animated use count. Loading → 8
 * shimmer rows; empty → renders nothing (the page suppresses the board).
 */
export function TopRankedBoard() {
  const { data, isLoading } = useTopRanked(8);

  if (isLoading) {
    return (
      <section style={{ marginBottom: 40 }}>
        <BoardHeading />
        <div style={{ display: "grid", gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Shimmer key={i} height={44} radius={RADIUS} />
          ))}
        </div>
      </section>
    );
  }

  const rows = data ?? [];
  if (rows.length === 0) return null;

  const top = Math.max(1, rows[0].downloads);

  return (
    <section style={{ marginBottom: 40 }}>
      <BoardHeading />
      <div style={{ display: "grid", gap: 8 }}>
        {rows.map((listing, i) => {
          const category = listing.category ?? listing.type ?? "skill";
          const share = Math.max(0.04, listing.downloads / top);
          return (
            <Reveal key={listing.id} delay={i * 45}>
              <Link
                to={`/marketplace/${listing.id}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 12px",
                  background: tokens.color.surface,
                  border: `1px solid ${tokens.color.line}`,
                  borderRadius: RADIUS,
                  textDecoration: "none",
                }}
              >
                <span
                  style={{
                    ...storefrontType.monoSmall,
                    color: tokens.color.ink3,
                    width: 20,
                    flexShrink: 0,
                  }}
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span aria-hidden style={swatchStyle(categoryAccentFor(category))} />
                <span
                  style={{
                    ...storefrontType.title,
                    fontSize: 14,
                    flex: "0 0 auto",
                    maxWidth: 260,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {listing.title}
                </span>
                {/* Proportional mini bar — share of #1 uses. */}
                <span
                  aria-hidden
                  style={{ flex: 1, height: 4, background: tokens.color.line, borderRadius: 2 }}
                >
                  <span
                    style={{
                      display: "block",
                      height: "100%",
                      width: `${Math.round(share * 100)}%`,
                      background: categoryAccentFor(category),
                      borderRadius: 2,
                    }}
                  />
                </span>
                <NumberTicker
                  value={listing.downloads}
                  style={{ ...storefrontType.mono, color: tokens.color.ink2, flexShrink: 0 }}
                />
              </Link>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

function BoardHeading() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 10,
        padding: "0 0 12px",
        marginBottom: 12,
        borderBottom: `1px solid ${tokens.color.line}`,
      }}
    >
      <span style={storefrontType.eyebrow}>TOP RANKED</span>
      <span style={{ ...storefrontType.monoSmall }}>by uses</span>
    </div>
  );
}

export default TopRankedBoard;
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/marketplace/components/__tests__/TopRankedBoard.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/marketplace/components/TopRankedBoard.tsx frontend/src/features/marketplace/components/__tests__/TopRankedBoard.test.tsx && git commit -m "$(cat <<'EOF'
feat(fe): TopRankedBoard leaderboard component

Numbered top-8-by-uses board with swatch, proportional bar, NumberTicker;
shimmer while loading, nothing when empty.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: marketplace — `TrendingMarquee` component

**Files:**
- Create: `frontend/src/features/marketplace/components/TrendingMarquee.tsx`
- Test: `frontend/src/features/marketplace/components/__tests__/TrendingMarquee.test.tsx`

**Interfaces:**
- Consumes: `usePublicCategories` (mocked in test), `Marquee`, `tokens`, `storefrontType`.
- Produces: `TrendingMarquee({ onPick }: { onPick: (category: string) => void }): JSX.Element | null` (null when no categories).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/marketplace/components/__tests__/TrendingMarquee.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../api/publicMarketplaceApi", () => ({ usePublicCategories: vi.fn() }));
// Marquee duplicates children in real life; render once here for a clean assert.
vi.mock("@/features/shared/fancy/Marquee", () => ({
  Marquee: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));

import { usePublicCategories } from "../../api/publicMarketplaceApi";
import { TrendingMarquee } from "../TrendingMarquee";

describe("TrendingMarquee", () => {
  it("renders a chip per category and fires onPick when clicked", () => {
    vi.mocked(usePublicCategories).mockReturnValue({
      data: [
        { category: "extraction", count: 12 },
        { category: "enrichment", count: 5 },
      ],
    } as unknown as ReturnType<typeof usePublicCategories>);
    const onPick = vi.fn();

    render(<TrendingMarquee onPick={onPick} />);
    const chip = screen.getByRole("button", { name: /extraction/i });
    expect(chip).toBeInTheDocument();
    fireEvent.click(chip);
    expect(onPick).toHaveBeenCalledWith("extraction");
  });

  it("renders nothing when there are no categories", () => {
    vi.mocked(usePublicCategories).mockReturnValue({
      data: [],
    } as unknown as ReturnType<typeof usePublicCategories>);
    const { container } = render(<TrendingMarquee onPick={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/marketplace/components/__tests__/TrendingMarquee.test.tsx`
Expected: FAIL — "Failed to resolve import ../TrendingMarquee".

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/features/marketplace/components/TrendingMarquee.tsx
import { tokens } from "@/app/theme/tokens";
import { Marquee } from "@/features/shared/fancy/Marquee";
import { RADIUS, storefrontType } from "@/features/marketplace/storefront";
import { categoryAccentFor } from "@/features/marketplace/theme";
import { usePublicCategories } from "../api/publicMarketplaceApi";

/**
 * A trending ribbon of category chips (top categories by count) that scrolls
 * seamlessly under the hero. Clicking a chip sets the category filter via
 * `onPick`. Renders nothing until categories load / when there are none.
 */
export function TrendingMarquee({ onPick }: { onPick: (category: string) => void }) {
  const { data } = usePublicCategories();
  const cats = (data ?? []).slice(0, 12);
  if (cats.length === 0) return null;

  return (
    <div style={{ marginBottom: 32 }}>
      <Marquee speed={40} pauseOnHover>
        {cats.map((c) => (
          <button
            key={c.category}
            type="button"
            onClick={() => onPick(c.category)}
            style={{
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: tokens.color.surface,
              border: `1px solid ${tokens.color.line}`,
              borderRadius: RADIUS,
              padding: "4px 10px",
              font: `500 12px ${tokens.font.sans}`,
              color: tokens.color.ink2,
              whiteSpace: "nowrap",
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: 1,
                background: categoryAccentFor(c.category),
              }}
            />
            <span style={{ textTransform: "capitalize" }}>{c.category}</span>
            <span style={{ ...storefrontType.monoSmall }}>{c.count}</span>
          </button>
        ))}
      </Marquee>
    </div>
  );
}

export default TrendingMarquee;
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/marketplace/components/__tests__/TrendingMarquee.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/marketplace/components/TrendingMarquee.tsx frontend/src/features/marketplace/components/__tests__/TrendingMarquee.test.tsx && git commit -m "$(cat <<'EOF'
feat(fe): TrendingMarquee category ribbon

Seamless marquee of top category chips; clicking a chip sets the category
filter via onPick.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: marketplace — `InfiniteSkillGrid` component

**Files:**
- Create: `frontend/src/features/marketplace/components/InfiniteSkillGrid.tsx`
- Test: `frontend/src/features/marketplace/components/__tests__/InfiniteSkillGrid.test.tsx`

**Interfaces:**
- Consumes: `useInfiniteMarketplace` (mocked), `useInView` (mocked to control the sentinel), `SkillCard`, `Spotlight`, `Reveal`, `Shimmer`, `tokens`, `GUTTER`, `RADIUS`.
- Produces: `InfiniteSkillGrid({ params, masonryClass }: { params: InfiniteParams; masonryClass: string }): JSX.Element`. Flattens `data.pages` into cards; a bottom sentinel calls `fetchNextPage()` when `useInView` reports visible **and** `hasNextPage`; shows a `Shimmer` row while `isFetchingNextPage`; renders an "end of results" hairline when `!hasNextPage` and there is data.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/marketplace/components/__tests__/InfiniteSkillGrid.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  Link: ({ children }: { children?: React.ReactNode }) => <a>{children}</a>,
}));
vi.mock("../../api/publicMarketplaceApi", () => ({ useInfiniteMarketplace: vi.fn() }));
// Control the sentinel: default to "in view" so an available next page fetches.
vi.mock("@/features/shared/fancy/useInView", () => ({ useInView: vi.fn() }));
vi.mock("@/features/shared/fancy/Reveal", () => ({
  Reveal: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/shared/fancy/Spotlight", () => ({
  Spotlight: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/shared/fancy/Shimmer", () => ({
  Shimmer: () => <div data-testid="shimmer" />,
}));

import { useInfiniteMarketplace } from "../../api/publicMarketplaceApi";
import { useInView } from "@/features/shared/fancy/useInView";
import { InfiniteSkillGrid } from "../InfiniteSkillGrid";

const card = (id: string) => ({
  id,
  title: `Card ${id}`,
  summary: "s",
  type: "skill",
  featured: false,
  version: "1",
  tags: [],
  downloads: 0,
});

function mockGrid(over: Record<string, unknown>) {
  vi.mocked(useInfiniteMarketplace).mockReturnValue({
    data: { pages: [[card("1"), card("2")], [card("3")]], pageParams: [0, 24] },
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    ...over,
  } as unknown as ReturnType<typeof useInfiniteMarketplace>);
}

describe("InfiniteSkillGrid", () => {
  it("flattens all pages into cards", () => {
    vi.mocked(useInView).mockReturnValue([{ current: null }, false]);
    mockGrid({});
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(screen.getByText("Card 1")).toBeInTheDocument();
    expect(screen.getByText("Card 2")).toBeInTheDocument();
    expect(screen.getByText("Card 3")).toBeInTheDocument();
  });

  it("calls fetchNextPage when the sentinel is in view and there is a next page", () => {
    const fetchNextPage = vi.fn();
    vi.mocked(useInView).mockReturnValue([{ current: null }, true]);
    mockGrid({ hasNextPage: true, fetchNextPage });
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it("does not fetch and shows the end marker when there is no next page", () => {
    const fetchNextPage = vi.fn();
    vi.mocked(useInView).mockReturnValue([{ current: null }, true]);
    mockGrid({ hasNextPage: false, fetchNextPage });
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(fetchNextPage).not.toHaveBeenCalled();
    expect(screen.getByText(/end of results/i)).toBeInTheDocument();
  });

  it("shows a shimmer row while fetching the next page", () => {
    vi.mocked(useInView).mockReturnValue([{ current: null }, false]);
    mockGrid({ hasNextPage: true, isFetchingNextPage: true });
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(screen.getAllByTestId("shimmer").length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/marketplace/components/__tests__/InfiniteSkillGrid.test.tsx`
Expected: FAIL — "Failed to resolve import ../InfiniteSkillGrid".

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/features/marketplace/components/InfiniteSkillGrid.tsx
import { useEffect } from "react";
import { tokens } from "@/app/theme/tokens";
import { Reveal } from "@/features/shared/fancy/Reveal";
import { Shimmer } from "@/features/shared/fancy/Shimmer";
import { Spotlight } from "@/features/shared/fancy/Spotlight";
import { useInView } from "@/features/shared/fancy/useInView";
import { GUTTER, RADIUS, storefrontType } from "@/features/marketplace/storefront";
import {
  useInfiniteMarketplace,
  type InfiniteParams,
  type PublicListing,
} from "../api/publicMarketplaceApi";
import { SkillCard } from "./SkillCard";

/**
 * The lazy-loading results grid. Flattens `useInfiniteMarketplace` pages into
 * the existing masonry wall (each card wrapped in Spotlight + Reveal, staggered
 * by index within its page), watches a bottom sentinel with `useInView`, and
 * calls `fetchNextPage` when the sentinel is visible and there is a next page.
 * Shows a shimmer row while fetching and an "end of results" hairline when done.
 */
export function InfiniteSkillGrid({
  params,
  masonryClass,
}: {
  params: InfiniteParams;
  masonryClass: string;
}) {
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteMarketplace(params);

  const [sentinelRef, sentinelInView] = useInView<HTMLDivElement>({ once: false, rootMargin: "300px" });

  useEffect(() => {
    if (sentinelInView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [sentinelInView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className={masonryClass}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
            <Shimmer height={180} radius={RADIUS} />
          </div>
        ))}
      </div>
    );
  }

  const pages = data?.pages ?? [];
  const flat: PublicListing[] = pages.flat();

  if (flat.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "60px 20px",
          color: tokens.color.ink3,
          font: `400 13px ${tokens.font.sans}`,
        }}
      >
        {params.q ? `No skills match "${params.q}".` : "No skills published yet."}
      </div>
    );
  }

  // Stagger delay resets per page so later pages don't accumulate huge delays.
  let pageOffset = 0;

  return (
    <>
      <div className={masonryClass}>
        {pages.map((page, pi) => {
          const base = pageOffset;
          pageOffset += page.length;
          return page.map((listing, i) => (
            <div key={listing.id} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
              <Reveal delay={Math.min(i, 8) * 40}>
                <Spotlight>
                  <SkillCard listing={listing} />
                </Spotlight>
              </Reveal>
            </div>
          ));
        })}
      </div>

      {isFetchingNextPage && (
        <div className={masonryClass}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
              <Shimmer height={160} radius={RADIUS} />
            </div>
          ))}
        </div>
      )}

      {/* Bottom sentinel — triggers the next page when scrolled near. */}
      <div ref={sentinelRef} aria-hidden style={{ height: 1 }} />

      {!hasNextPage && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            margin: "28px 0 0",
            color: tokens.color.ink3,
          }}
        >
          <span style={{ flex: 1, height: 1, background: tokens.color.line }} />
          <span style={{ ...storefrontType.monoSmall }}>end of results</span>
          <span style={{ flex: 1, height: 1, background: tokens.color.line }} />
        </div>
      )}
    </>
  );
}

export default InfiniteSkillGrid;
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/marketplace/components/__tests__/InfiniteSkillGrid.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/marketplace/components/InfiniteSkillGrid.tsx frontend/src/features/marketplace/components/__tests__/InfiniteSkillGrid.test.tsx && git commit -m "$(cat <<'EOF'
feat(fe): InfiniteSkillGrid lazy-loading grid

Flattens infinite-query pages into the masonry wall, wraps cards in
Spotlight+Reveal, a useInView sentinel drives fetchNextPage, end-of-results
hairline when done.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: marketplace — `MarketplacePage` integration

**Files:**
- Modify: `frontend/src/features/marketplace/pages/MarketplacePage.tsx`
- Test: `frontend/src/features/marketplace/pages/__tests__/MarketplacePage.test.tsx`

**Interfaces:**
- Consumes: `GradientText`, `Magnetic`, `TrendingMarquee`, `TopRankedBoard`, `InfiniteSkillGrid`, existing `usePublicCategories`, `useTaxonomyTerms`.
- Produces: default-exported `MarketplacePage`. New derived flag: `isBrowsingDefault = !q && !category && !capability && !source` gates `TopRankedBoard`. The single-shot list is replaced by `InfiniteSkillGrid` fed `{ q, type: undefined, category, sort, capability, source }`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/marketplace/pages/__tests__/MarketplacePage.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  Link: ({ children }: { children?: React.ReactNode }) => <a>{children}</a>,
}));
// Categories + taxonomy hooks used by the hero/filters.
vi.mock("../../api/publicMarketplaceApi", () => ({
  usePublicCategories: vi.fn(() => ({ data: [{ category: "extraction", count: 3 }] })),
}));
vi.mock("@/features/concepts/api/taxonomyApi", () => ({
  useTaxonomyTerms: vi.fn(() => ({ data: { terms: [] } })),
}));
// Board renders a marker only when mounted; grid renders a marker always.
vi.mock("../../components/TopRankedBoard", () => ({
  TopRankedBoard: () => <div data-testid="board" />,
}));
vi.mock("../../components/TrendingMarquee", () => ({
  TrendingMarquee: ({ onPick }: { onPick: (c: string) => void }) => (
    <button type="button" onClick={() => onPick("extraction")}>
      pick-extraction
    </button>
  ),
}));
vi.mock("../../components/InfiniteSkillGrid", () => ({
  InfiniteSkillGrid: () => <div data-testid="grid" />,
}));

import MarketplacePage from "../MarketplacePage";

describe("MarketplacePage", () => {
  it("shows the TopRankedBoard by default and always shows the grid", () => {
    render(<MarketplacePage />);
    expect(screen.getByTestId("board")).toBeInTheDocument();
    expect(screen.getByTestId("grid")).toBeInTheDocument();
  });

  it("hides the TopRankedBoard once a category filter is applied", () => {
    render(<MarketplacePage />);
    // TrendingMarquee's pick sets the category filter → board unmounts.
    fireEvent.click(screen.getByText("pick-extraction"));
    expect(screen.queryByTestId("board")).not.toBeInTheDocument();
    expect(screen.getByTestId("grid")).toBeInTheDocument();
  });

  it("hides the TopRankedBoard once a search query is typed", () => {
    render(<MarketplacePage />);
    fireEvent.change(screen.getByLabelText(/search skills/i), {
      target: { value: "csv" },
    });
    expect(screen.queryByTestId("board")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/marketplace/pages/__tests__/MarketplacePage.test.tsx`
Expected: FAIL — the current page imports `usePublicMarketplace`/`SkillCard`/`Skeleton` and renders neither `TopRankedBoard` nor `InfiniteSkillGrid`; `getByTestId("board")` and `getByTestId("grid")` are not found. (The query-typed case fails because the board is not conditional.)

- [ ] **Step 3: Write the minimal implementation**

Replace `frontend/src/features/marketplace/pages/MarketplacePage.tsx` with (the hero/filter markup is preserved verbatim except the noted swaps — `GradientText` headline, `Magnetic` search wrapper, `TrendingMarquee` under the filters, and the results block replaced by `TopRankedBoard` + `InfiniteSkillGrid`):

```tsx
import { SearchOutlined } from "@ant-design/icons";
import { Input } from "antd";
import { useEffect, useMemo, useState } from "react";
import { tokens } from "@/app/theme/tokens";
import { GUTTER, RADIUS, storefrontType } from "@/features/marketplace/storefront";
import { GradientText } from "@/features/shared/fancy/GradientText";
import { Magnetic } from "@/features/shared/fancy/Magnetic";
import { usePublicCategories, type SortKey } from "../api/publicMarketplaceApi";
import { InfiniteSkillGrid } from "../components/InfiniteSkillGrid";
import { TopRankedBoard } from "../components/TopRankedBoard";
import { TrendingMarquee } from "../components/TrendingMarquee";
import { useTaxonomyTerms } from "@/features/concepts/api/taxonomyApi";

const MASONRY_CLASS = "marketplace-masonry";

/**
 * Responsive masonry column count via inline media queries: 4 at ≥1200px,
 * 3 at ≥900px, 2 at ≥600px, 1 below. Scoped to MASONRY_CLASS so it doesn't
 * leak outside this page.
 */
function MasonryResponsiveStyle() {
  return (
    <style>{`
      .${MASONRY_CLASS} { column-count: 1; column-gap: ${GUTTER}px; }
      @media (min-width: 600px) { .${MASONRY_CLASS} { column-count: 2; } }
      @media (min-width: 900px) { .${MASONRY_CLASS} { column-count: 3; } }
      @media (min-width: 1200px) { .${MASONRY_CLASS} { column-count: 4; } }
    `}</style>
  );
}

export default function MarketplacePage() {
  const [category, setCategory] = useState<string | undefined>();
  const [capability, setCapability] = useState<string | undefined>();
  const [source, setSource] = useState<string | undefined>();
  const [sort, setSort] = useState<SortKey>("uses");
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");

  // Debounce the search input (~250ms) before it drives the query.
  useEffect(() => {
    const timer = setTimeout(() => setQ(qInput.trim()), 250);
    return () => clearTimeout(timer);
  }, [qInput]);

  const categories = usePublicCategories();
  const capabilityTerms = useTaxonomyTerms("capabilities");
  const sourceTerms = useTaxonomyTerms("sources");

  // Stable total across the whole catalog — sums the category counts.
  const totalCount = useMemo(() => {
    const cats = categories.data;
    if (!cats || cats.length === 0) return 0;
    return cats.reduce((sum, c) => sum + c.count, 0);
  }, [categories.data]);

  // The leaderboard is a global "best of": show it only while browsing the
  // default view — no search text and no facet/category selection.
  const isBrowsingDefault = !q && !category && !capability && !source;

  return (
    <div style={{ paddingBottom: 60 }}>
      <MasonryResponsiveStyle />
      {/* Hero: centered headline, count, search, category filters */}
      <div style={{ padding: "56px 0 40px", textAlign: "center" }}>
        <h1
          style={{
            margin: 0,
            font: `600 40px/1.15 ${tokens.font.sans}`,
            letterSpacing: "-0.02em",
          }}
        >
          <GradientText>Find a data skill</GradientText>
        </h1>
        <div
          style={{
            marginTop: 10,
            font: `500 12px/1.4 ${tokens.font.mono}`,
            color: tokens.color.ink3,
          }}
        >
          {totalCount} skills · content-addressed
        </div>

        <div style={{ margin: "28px auto 0", maxWidth: 560 }}>
          <Magnetic strength={0.15}>
            <div style={{ width: 560, maxWidth: "100%" }}>
              <Input
                allowClear
                size="large"
                prefix={<SearchOutlined style={{ color: tokens.color.ink3 }} aria-hidden />}
                placeholder="Search skills…"
                aria-label="Search skills"
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                style={{
                  borderRadius: RADIUS,
                  border: `1px solid ${tokens.color.line}`,
                  boxShadow: "none",
                }}
              />
            </div>
          </Magnetic>
        </div>

        {/* Category filters — the active one carries the only red marker. */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            flexWrap: "wrap",
            gap: 18,
            marginTop: 24,
          }}
        >
          <CategoryFilter label="All" isActive={!category} onClick={() => setCategory(undefined)} />
          {(categories.data ?? []).map((c) => (
            <CategoryFilter
              key={c.category}
              label={c.category}
              isActive={category === c.category}
              onClick={() => setCategory(category === c.category ? undefined : c.category)}
            />
          ))}
        </div>

        {/* Capability facets */}
        {(capabilityTerms.data?.terms ?? []).length > 0 && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              flexWrap: "wrap",
              gap: 14,
              marginTop: 16,
              paddingTop: 12,
              borderTop: `1px solid ${tokens.color.line}`,
            }}
          >
            <span
              style={{
                font: `500 11px/1 ${tokens.font.mono}`,
                color: tokens.color.ink3,
                alignSelf: "center",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              capability
            </span>
            <FacetFilter label="Any" isActive={!capability} onClick={() => setCapability(undefined)} />
            {(capabilityTerms.data?.terms ?? []).map((t) => (
              <FacetFilter
                key={t.key}
                label={t.label}
                isActive={capability === t.key}
                onClick={() => setCapability(capability === t.key ? undefined : t.key)}
              />
            ))}
          </div>
        )}

        {/* Source facets */}
        {(sourceTerms.data?.terms ?? []).length > 0 && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              flexWrap: "wrap",
              gap: 14,
              marginTop: 10,
            }}
          >
            <span
              style={{
                font: `500 11px/1 ${tokens.font.mono}`,
                color: tokens.color.ink3,
                alignSelf: "center",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              source
            </span>
            <FacetFilter label="Any" isActive={!source} onClick={() => setSource(undefined)} />
            {(sourceTerms.data?.terms ?? []).map((t) => (
              <FacetFilter
                key={t.key}
                label={t.label}
                isActive={source === t.key}
                onClick={() => setSource(source === t.key ? undefined : t.key)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Trending category ribbon — clicking a chip sets the category filter. */}
      <TrendingMarquee onPick={(c) => setCategory(c)} />

      {/* Fixed leaderboard — only while browsing the default view. */}
      {isBrowsingDefault && <TopRankedBoard />}

      {/* Section header: eyebrow + sort toggle */}
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          padding: "0 0 16px",
          borderBottom: `1px solid ${tokens.color.line}`,
          marginBottom: GUTTER,
        }}
      >
        <span style={storefrontType.eyebrow}>EXPLORE</span>
        <button
          type="button"
          onClick={() => setSort(sort === "uses" ? "recent" : "uses")}
          style={{
            marginLeft: "auto",
            cursor: "pointer",
            background: "none",
            border: "none",
            padding: 0,
            font: `500 12px ${tokens.font.sans}`,
            color: tokens.color.ink2,
          }}
        >
          {sort === "uses" ? "Trending" : "Newest"}
        </button>
      </div>

      {/* Lazy-loading results grid. */}
      <InfiniteSkillGrid
        params={{ q, type: undefined, category, sort, capability, source }}
        masonryClass={MASONRY_CLASS}
      />
    </div>
  );
}

function CategoryFilter({
  label,
  isActive,
  onClick,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        cursor: "pointer",
        background: "none",
        border: "none",
        padding: "2px 0",
        font: `${isActive ? 600 : 400} 13px ${tokens.font.sans}`,
        color: isActive ? tokens.color.ink : tokens.color.ink2,
        textTransform: "capitalize",
        position: "relative",
      }}
    >
      {label}
      {isActive && (
        <span
          aria-hidden
          style={{
            display: "block",
            position: "absolute",
            left: 0,
            right: 0,
            bottom: -4,
            height: 2,
            background: tokens.color.accent,
            borderRadius: 1,
          }}
        />
      )}
    </button>
  );
}

/**
 * Lightweight facet filter pill — matches the Swiss restraint of CategoryFilter.
 * Active state: red underline tick only (no fill); label weight increases.
 */
function FacetFilter({
  label,
  isActive,
  onClick,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        cursor: "pointer",
        background: "none",
        border: `1px solid ${isActive ? tokens.color.accent : tokens.color.line}`,
        borderRadius: 4,
        padding: "2px 8px",
        font: `${isActive ? 600 : 400} 11px ${tokens.font.sans}`,
        color: isActive ? tokens.color.ink : tokens.color.ink2,
        position: "relative",
        transition: "border-color 0.15s",
      }}
    >
      {label}
      {isActive && (
        <span
          aria-hidden
          style={{
            display: "block",
            position: "absolute",
            left: 4,
            right: 4,
            bottom: -3,
            height: 2,
            background: tokens.color.accent,
            borderRadius: 1,
          }}
        />
      )}
    </button>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/marketplace/pages/__tests__/MarketplacePage.test.tsx`
Expected: PASS (3 tests). Then the full frontend suite + typecheck + build:
`cd frontend && npm test -- run` → all green; `npx tsc --noEmit` → clean; `npm run build` → succeeds.

- [ ] **Step 5: Commit**

```
cd "/Users/josephkiype/Desktop/development/code/agent skills framework" && git add frontend/src/features/marketplace/pages/MarketplacePage.tsx frontend/src/features/marketplace/pages/__tests__/MarketplacePage.test.tsx && git commit -m "$(cat <<'EOF'
feat(fe): MarketplacePage home — gradient hero, marquee, leaderboard, lazy grid

GradientText headline + Magnetic search; TrendingMarquee under the hero;
TopRankedBoard shown only when browsing default (no query/category/facet);
InfiniteSkillGrid replaces the single-shot list.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Final verification (after Task 11)

- Backend: `cd backend && uv run --python 3.12 --extra dev pytest tests/integration/test_marketplace_pagination.py tests/integration/test_marketplace_facets.py tests/integration/test_public_marketplace.py -q` → PASS (or SKIPPED without live services).
- Frontend: `cd frontend && npm test -- run` → all green; `npx tsc --noEmit` → clean; `npm run build` → succeeds.
- Manual smoke (optional): `cd frontend && npm run dev`, open `/` — leaderboard visible by default, disappears on search/category; grid lazy-loads on scroll; motion respects an OS "reduce motion" setting.

---

## Self-Review

**Spec coverage** — every §3–§7 item is mapped:
- §3.1 SQL category filter via `coalesce(category, type)` → Task 1. §3.2 `offset` + secondary `id` order → Task 1. §3.3 service pass-through (post-filter removed) + endpoint `limit`/`offset` clamp → Task 2.
- §4 `useInfiniteMarketplace` (`getNextPageParam` = `allPages.length * pageSize` when full) + `useTopRanked` (own key, no filters); `usePublicMarketplace` retained → Task 7.
- §5 `usePrefersReducedMotion` (Task 3), `useInView` (Task 3), `Reveal` + `Shimmer` + `fancy.css` (Task 4), `Magnetic` + `GradientText` (Task 5), `Marquee` + `Spotlight` (Task 6) — all reduced-motion-degrading, no new deps.
- §6 `TopRankedBoard` (Task 8), `TrendingMarquee` (Task 9), `InfiniteSkillGrid` (Task 10), `MarketplacePage` composition with `isBrowsingDefault` gate (Task 11).
- §7 test matrix: repo coalesce + offset (T1), endpoint clamp (T2), `useInView`/`usePrefersReducedMotion` (T3), `Reveal`/`Magnetic`/`Marquee` reduced-motion (T4–T6), `TopRankedBoard` ranked/empty/loading (T8), `InfiniteSkillGrid` flatten/sentinel/end (T10), `MarketplacePage` board present-by-default / absent-when-filtered (T11).

**Placeholder scan** — no `TODO`, no "similar to Task N", no elided bodies: every implementation block is complete and copy-pasteable.

**Type consistency** — `InfiniteParams.sort: SortKey` (required) matches `MarketplacePage` always passing `sort`. `useInfiniteMarketplace` returns react-query's `useInfiniteQuery` result whose `data.pages` is `PublicListing[][]` (matching `InfiniteSkillGrid`'s `pages.flat()`). `useInView` returns `[React.RefObject<T>, boolean]`; `InfiniteSkillGrid` binds `sentinelRef` to a `<div>` and passes `{ once: false, rootMargin }`. Backend `list(...)` new kwargs `category`/`offset` are keyword-only (`*,`) and defaulted, so existing callers (`public_categories` uses `limit=` only; `most_installed` untouched) still type-check. `Shimmer.height` accepts `number | string`; callers pass numbers.

**Resolved ambiguities**
1. **Secondary sort replacement:** the current `list` already appends `desc(created_at)` as a secondary sort. The spec asks for a *stable, unique* tiebreaker; `created_at` is not unique. Resolved by **replacing** the secondary `created_at` with `MarketplaceListing.id` (unique PK) so offset paging is provably disjoint on ties — this is what the disjoint-slices test asserts.
2. **Total count display:** the old header showed `EXPLORE · {data.length}`, but with pagination `data.length` is only the loaded page count and would be misleading. Resolved by dropping the per-result count from the EXPLORE eyebrow (kept the hero's catalog-wide `totalCount` from category sums, which is stable). This is within spec §6's "keep filters/sort as-is" since the count was cosmetic, not a filter.
3. **Endpoint test envelope/prefix:** the response is wrapped by `success(...)` under `data`, and the router mount prefix must match the existing `test_public_marketplace.py`. The plan uses `/api/v1/public/marketplace` and `r.json()["data"]`; Task 2 Step 1 notes to align both with that existing test if the mount differs.
4. **`Magnetic` on antd `Input`:** antd's `Input` doesn't forward arbitrary refs cleanly, so `Magnetic` wraps a plain `<div>` around the `Input` (translating the wrapper, not the `Input` internals) — preserving the existing search box behavior and `aria-label`.
