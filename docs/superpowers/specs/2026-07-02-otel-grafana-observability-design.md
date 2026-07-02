# OTel/Grafana Observability + In-App Skill-Usage Analytics — Design Spec

**Date:** 2026-07-02
**Branch:** `feat/otel-grafana-observability` (to be created off `main`)
**Status:** Approved (pending spec review) — ready for implementation planning
**Builds on:** the durable usage audit trail (`UsageEvent`, `usage_events` table,
`MarketplaceRepository.add_usage`), the three usage-write call sites in
`MarketplaceService` (`fetch_skill` → `fetch`, `clone_to_workspace` → `clone`,
`report_usage` → `apply`), the existing `structlog` + trace-id middleware
(`app/core/logging.py`, `app/main.py`), the pydantic `Settings`
(`app/core/config.py`), and the existing analytics surface
(`AnalyticsService.overview`, `GET /analytics/overview`,
`frontend/src/features/insights/`).
**Roadmap position:** Workstream **D** of the six-part marketplace build
(A rich editor ✓ → B per-skill stats/clone ✓ → C home ranking + lazy load + motion ✓ →
**D OTel/Grafana observability + in-app usage analytics** → E framework adapters →
F design studio).

## 1. Summary

Add an OpenTelemetry-based observability layer that turns skill usage into live,
queryable telemetry without disturbing the request path, **plus an in-app "Skill Usage"
analytics page** so usage insight lives in the product, not only in ops tooling.

Two independent read paths sit on top of the same durable audit trail:

1. **Ops / deep-dive (Grafana).** The backend (which runs natively via `uv`) gains an
   OTel SDK that exports **metrics and traces** over OTLP/gRPC to an `otel-collector`,
   which fans out to **Prometheus** (metrics) and **Tempo** (traces); **Grafana** sits on
   top with datasources and a "Skill Usage" dashboard **provisioned as code** so
   `docker compose up` yields live dashboards with zero manual clicks.
2. **In-product (app UI).** A new `GET /analytics/usage` endpoint aggregates the
   `usage_events` table directly, and a new animated frontend **Skill Usage** page
   (built with **framer-motion + gsap**) renders KPIs, framework/outcome breakdowns, top
   skills, and an applies-over-time series. Because it reads Postgres directly, this page
   works **even when the observability stack is not running**.

The durable, auditable foundation already exists: `UsageEvent` rows record every
`fetch`/`apply`/`clone` with API-key attribution. D adds both read paths and **emits each
OTel metric at the same service-layer point that writes the audit row**, so audit,
metrics, and the in-app aggregates stay consistent.

D also defines the **trackable contract** that Workstream E's per-framework adapters will
call: the SDK usage report (`POST /sdk/usage`) is extended with optional `framework`,
`outcome`, and `duration_ms` fields, server-normalized to a bounded allow-list. The
adapter *packages themselves* are E, not D.

## 2. Decisions (locked with user)

- **Stack depth:** metrics **and** traces via a collector. OTel SDK → OTLP/gRPC →
  `otel-collector` → Prometheus (metrics) + Tempo (traces) → Grafana. No logs pillar
  (structlog JSON + the Postgres audit trail already cover it). Four new Docker services.
- **Traces backend:** **Tempo** (tighter Grafana integration than Jaeger).
- **Core skill-usage metric labels:** `kind` (fetch/apply/clone), `framework`,
  `skill` (listing id/slug), `outcome` (ok/error). No raw user IDs or free-text as
  labels (cardinality safety).
- **Trackable contract:** extend `POST /sdk/usage` now with optional `framework`,
  `outcome`, `duration_ms`; normalize `framework` server-side to the allow-list
  `{langgraph, langchain, google-adk, claude, copilot, other}` (unknown → `other`).
  Backward compatible.
- **In-app analytics page:** add a frontend **Skill Usage** page (under
  `features/insights/`) fed by a new `GET /analytics/usage` endpoint reading
  `usage_events`. Grafana stays for ops/trace deep-dives.
- **Frontend motion libraries:** adopt **framer-motion** and **gsap** as approved
  frontend dependencies (this supersedes the prior "no new dependencies" rule *for the
  frontend*). The new page uses them for KPI count-ups (gsap) and card/section reveals
  and transitions (framer-motion). The backend/ops side adds no new *runtime* deps beyond
  the OTel packages.
- **Fail-open (hard constraint):** all OTel instrumentation is a no-op when
  `otel_enabled` is false **or** the collector is unreachable. Observability must never
  break a request or the audit write. Local dev without the stack runs unchanged.
- **Reduced motion (hard constraint, unchanged house rule):** every framer-motion / gsap
  effect degrades to a static final state under `prefers-reduced-motion: reduce`
  (framer-motion `useReducedMotion()`; gsap gated by the existing
  `usePrefersReducedMotion` hook).

## 3. Architecture & data flow

```
FastAPI backend (native, uv)
  ├─ writes UsageEvent row (Postgres)  ── durable audit trail (source of truth)
  │     ▲ fetch_skill / clone_to_workspace / report_usage
  │
  ├─ OTel SDK (traces + metrics), OTLP/gRPC exporter → collector:4317   [ops path]
  │    • auto-instrumentation: FastAPI (HTTP spans + request metrics),
  │      SQLAlchemy, asyncpg
  │    • custom counter:   eakso_skill_usage_total{kind,framework,skill,outcome}
  │    • custom histogram: eakso_skill_apply_duration_seconds{framework,skill}
  │    • emitted alongside every add_usage() write
  │        │  OTLP/gRPC
  │        ▼
  │   otel-collector (docker) → Prometheus (metrics) + Tempo (traces)
  │        ▼
  │      Grafana (docker) — datasources + dashboards provisioned as code
  │
  └─ GET /analytics/usage  → aggregates usage_events directly           [in-product path]
         ▲
      frontend Skill Usage page (framer-motion + gsap), reads via react-query
      — works even when the observability stack is down
```

Four new Docker services (`otel-collector`, `prometheus`, `tempo`, `grafana`) added to
the existing `docker-compose.yml`, consistent with "Docker only for data services." The
backend stays native.

## 4. Backend instrumentation (ops path)

### 4.1 Dependencies (`backend/pyproject.toml`)
Add: `opentelemetry-sdk`, `opentelemetry-exporter-otlp`,
`opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`,
`opentelemetry-instrumentation-asyncpg`. (Instrumentation is lazy; when telemetry is
disabled these import but do nothing.)

### 4.2 `app/core/telemetry.py` (new)
- `init_telemetry(app: FastAPI) -> None` — the single entry point.
  - No-op and early-return when `settings.otel_enabled` is false.
  - Builds a `Resource` with `service.name = settings.otel_service_name`.
  - Sets up `TracerProvider` + OTLP span exporter (when `otel_traces_enabled`) and
    `MeterProvider` + OTLP metric exporter (when `otel_metrics_enabled`), both pointing
    at `settings.otel_exporter_endpoint`.
  - Registers FastAPI, SQLAlchemy, and asyncpg auto-instrumentation.
  - Creates and stores module-level instruments: the `eakso_skill_usage_total` counter
    and `eakso_skill_apply_duration_seconds` histogram.
  - Exporter failures (collector down) must be swallowed by the SDK's batch processor —
    verify the exporter is constructed so a dead endpoint logs-and-drops rather than
    raising into the request path.
- `record_skill_usage(*, kind: str, framework: str, skill: str, outcome: str,
  duration_ms: float | None = None) -> None` — increments the counter with the four
  labels; records the histogram when `duration_ms` is provided; **no-op when telemetry
  is uninitialized/disabled** (guard on a module flag). Never raises.
- `normalize_framework(value: str | None) -> str` — lower/trim, map to the allow-list
  `{langgraph, langchain, google-adk, claude, copilot, other}`, unknown/empty → `other`.
  Pure function (unit-testable without any OTel setup).

### 4.3 `app/core/config.py` (`Settings`)
Add fields (env-overridable): `otel_enabled: bool = False`,
`otel_service_name: str = "eakso-backend"`,
`otel_exporter_endpoint: str = "http://localhost:4317"`,
`otel_traces_enabled: bool = True`, `otel_metrics_enabled: bool = True`.

### 4.4 `app/main.py`
Call `init_telemetry(app)` inside `create_app()` (after CORS/trace middleware, before
`register_error_handlers(app)`).

### 4.5 `app/services/marketplace_service.py`
At each of the three existing `add_usage(...)` sites, add a paired
`record_skill_usage(...)` call so the metric and the durable audit row are emitted
together:
- `fetch_skill` → `kind="fetch"`, `framework` from context/default `other`,
  `skill=<listing id/slug>`, `outcome="ok"`.
- `clone_to_workspace` → `kind="clone"`, `skill=<listing id/slug>`, `outcome="ok"`.
- `report_usage` → `kind` (default `apply`), `framework=normalize_framework(...)`,
  `outcome` (default `ok`), `duration_ms` when supplied.

### 4.6 `POST /sdk/usage` contract (`app/api/v1/routers/sdk.py` + `report_usage`)
Extend the request body with optional `framework: str | None`, `outcome: str | None`,
`duration_ms: float | None`. In `report_usage`:
- `framework = normalize_framework(payload.framework)`.
- `outcome = payload.outcome or "ok"`.
- Persist `framework`, `outcome`, `duration_ms` into `UsageEvent.meta` (audit) **and**
  pass them to `record_skill_usage(...)` (metrics).
- Fully backward compatible: all three fields optional; omitting them yields
  `framework="other"`, `outcome="ok"`, no duration recorded.

## 5. Backend usage-analytics read path (in-product path)

### 5.1 `MarketplaceRepository.usage_analytics(days: int = 30) -> dict` (new)
Aggregates the `usage_events` table over the last `days` days (Postgres):
- `total`: total event count in the window.
- `by_kind`: `[{ "kind": str, "count": int }]` grouped by `kind`.
- `by_framework`: `[{ "framework": str, "count": int }]` grouped by
  `coalesce(meta ->> 'framework', 'other')`.
- `by_outcome`: `[{ "outcome": str, "count": int }]` grouped by
  `coalesce(meta ->> 'outcome', 'ok')`.
- `top_skills`: `[{ "listing_id": str, "title": str, "uses": int }]` — join
  `marketplace_listings`, `kind = 'apply'`, ordered by `uses desc`, limit 10.
- `series`: `[{ "date": "YYYY-MM-DD", "applies": int }]` — daily bucket of
  `kind = 'apply'` (`date_trunc('day', created_at)`), ordered by date; days with no
  applies omitted (frontend interpolates).
Empty history yields empty lists and `total = 0`.

### 5.2 `AnalyticsService.usage(*, days: int = 30) -> dict` (new)
Thin wrapper: clamps `days` to `1..365` and returns
`repo.usage_analytics(days=days)`.

### 5.3 `GET /analytics/usage?days=30` (`app/api/v1/routers/analytics.py`)
New route guarded by `require_permission("skill:read")` (mirrors `/analytics/overview`),
returns the `success(...)` envelope wrapping `AnalyticsService(db).usage(days=days)`.
Reads Postgres only — independent of the OTel/Grafana stack.

## 6. Frontend — in-app Skill Usage analytics page (framer-motion + gsap)

### 6.1 Dependencies (`frontend/package.json`)
Add `framer-motion` and `gsap`. (Approved this workstream; see §2.)

### 6.2 `features/insights/api/analyticsApi.ts` (extend)
Add the `UsageAnalytics` types (mirroring §5.1: `total`, `by_kind`, `by_framework`,
`by_outcome`, `top_skills`, `series`) and
`useUsageAnalytics(days = 30)` — react-query over `GET /analytics/usage` with key
`["analytics-usage", days]`.

### 6.3 `features/insights/components/` (new)
- `GsapCountUp.tsx` — tweens a number from 0 → `value` with a gsap timeline on mount;
  renders the final value immediately under `usePrefersReducedMotion`. (gsap-based
  count-up, distinct from C's native `NumberTicker`.)
- `MotionSection.tsx` — thin framer-motion wrapper (`motion.div` with an
  enter/whileInView variant + stagger) that renders children statically when
  framer-motion's `useReducedMotion()` returns true. Used to reveal cards/sections.

### 6.4 `features/insights/pages/SkillUsagePage.tsx` (new)
Consumes `useUsageAnalytics(days)` with a day-range `Select` (7/30/90). Layout, all
wrapped in `MotionSection` with staggered reveals:
- **KPI row:** total uses, applies, clones, error rate (`by_outcome` error share) — each
  value animated with `GsapCountUp`.
- **Usage by framework:** recharts bar/horizontal-bar from `by_framework`, revealing on
  scroll.
- **Outcome split:** ok vs error (recharts) driving the error-rate KPI.
- **Top skills:** table/list from `top_skills` (title + uses), each row linking to
  `/marketplace/:listing_id`.
- **Applies over time:** recharts area/line from `series`.
- Empty states when `total === 0`. Styling from `@/app/theme/tokens` (Swiss-minimal,
  matching `InsightsPage`).

### 6.5 Routing & navigation
Register the page in the app router (sibling of the existing Insights route) and add a
nav entry ("Skill Usage" / "Usage") next to Insights, following the existing route/nav
pattern.

## 7. Observability config as code (`ops/observability/`, new, committed)

- `otel-collector-config.yaml` — OTLP receiver (gRPC :4317, HTTP :4318) → exporters:
  Prometheus (metrics) + Tempo (traces via OTLP).
- `prometheus.yml` — receives/scrapes the collector's metrics.
- `tempo.yaml` — minimal single-binary Tempo config (local storage).
- `grafana/provisioning/datasources/datasources.yaml` — Prometheus + Tempo datasources
  auto-wired.
- `grafana/provisioning/dashboards/dashboards.yaml` — dashboard provider pointing at:
- `grafana/dashboards/skill-usage.json` — the **"Skill Usage"** Grafana dashboard:
  total applies/fetches/clones, top skills by use, usage broken down by framework,
  error rate (outcome=error share), and HTTP latency p50/p95/p99 (from FastAPI
  auto-instrumentation).

## 8. Docker (`docker-compose.yml`)

Add four services wired to the `ops/observability/` configs, each with a health check
and named volumes where needed:
- `otel-collector` (`otel/opentelemetry-collector-contrib`) — ports 4317/4318, mounts
  `otel-collector-config.yaml`.
- `prometheus` (`prom/prometheus`) — port 9090, mounts `prometheus.yml`.
- `tempo` (`grafana/tempo`) — mounts `tempo.yaml`.
- `grafana` (`grafana/grafana`) — port 3000, mounts the provisioning dirs; anonymous
  admin for local dev (documented as dev-only).

The backend continues to run natively; it reaches the collector at
`otel_exporter_endpoint` (default `http://localhost:4317`).

## 9. Testing (TDD)

**Backend (pytest)**
- `normalize_framework`: known values pass through (case/space-insensitive); unknown and
  empty/None → `other`; the five named frameworks map exactly.
- `init_telemetry`: with `otel_enabled=false` it is a no-op (no provider set, no raise);
  `record_skill_usage` is safe to call before/without init (no raise, no effect).
- `record_skill_usage` label wiring: with telemetry initialized against an in-memory
  metric reader, calling it increments `eakso_skill_usage_total` with the exact
  `{kind,framework,skill,outcome}` labels; `duration_ms` records the histogram; omitting
  it does not.
- `report_usage` / `POST /sdk/usage`: normalizes `framework` to the allow-list
  (unknown → `other`), defaults `outcome="ok"`, persists the new fields into
  `UsageEvent.meta`, and stays backward-compatible when the fields are omitted.
- `usage_analytics` / `GET /analytics/usage`: seed `usage_events` across kinds,
  frameworks, outcomes and days → asserts `by_kind`/`by_framework`/`by_outcome` counts,
  `top_skills` ordering + titles, `series` daily buckets, `days` clamping, and the empty
  case (`total=0`, empty lists). Endpoint requires `skill:read`.

**Frontend (Vitest)**
- `GsapCountUp`: renders the final value immediately under reduced motion (mock
  `matchMedia`); renders a number node otherwise.
- `MotionSection`: renders its children (present in the DOM) both with and without
  reduced motion.
- `useUsageAnalytics` / `SkillUsagePage`: with the hook mocked, renders the KPI values,
  framework/top-skill breakdowns, and computes the error-rate; shows empty states when
  `total === 0`.

**Config**
- A parse test that loads every file under `ops/observability/` (collector, prometheus,
  tempo, grafana provisioning YAML) with a YAML parser so a malformed config fails the
  test suite rather than `docker compose up`. The Grafana dashboard JSON is validated as
  well-formed JSON.

No Grafana dashboard-behavior unit tests (panels validated only as parseable JSON +
provisioning).

## 10. Files touched

**Backend**
- `backend/pyproject.toml` — OTel SDK + exporter + instrumentation deps.
- `backend/app/core/telemetry.py` (new) — `init_telemetry`, `record_skill_usage`,
  `normalize_framework`, module instruments.
- `backend/app/core/config.py` — `otel_*` settings.
- `backend/app/main.py` — call `init_telemetry(app)`.
- `backend/app/services/marketplace_service.py` — `record_skill_usage` at the three
  `add_usage` sites; extended `report_usage` signature.
- `backend/app/api/v1/routers/sdk.py` — `framework`/`outcome`/`duration_ms` on the
  `POST /sdk/usage` body.
- `backend/app/repositories/marketplace_repo.py` — `usage_analytics(days)`.
- `backend/app/services/analytics_service.py` — `usage(days)`.
- `backend/app/api/v1/routers/analytics.py` — `GET /analytics/usage`.
- `backend/tests/...` — telemetry, normalize, sdk-usage, usage-analytics, and
  config-parse tests.

**Frontend**
- `frontend/package.json` — add `framer-motion`, `gsap`.
- `frontend/src/features/insights/api/analyticsApi.ts` — `UsageAnalytics` types +
  `useUsageAnalytics`.
- `frontend/src/features/insights/components/GsapCountUp.tsx`,
  `MotionSection.tsx` (new).
- `frontend/src/features/insights/pages/SkillUsagePage.tsx` (new).
- app router + nav — register the Skill Usage route/link.
- corresponding Vitest tests.

**Ops**
- `ops/observability/otel-collector-config.yaml`, `prometheus.yml`, `tempo.yaml`,
  `grafana/provisioning/datasources/datasources.yaml`,
  `grafana/provisioning/dashboards/dashboards.yaml`,
  `grafana/dashboards/skill-usage.json` (all new).
- `docker-compose.yml` — four observability services.

## 11. Out of scope (future workstreams)

The per-framework SDK **adapter packages** (E) — D defines only the trackable contract
they call. Also deferred unless needed: Prometheus alerting rules, long-term metric
retention/downsampling, multi-tenant Grafana orgs, a logs (Loki) pillar, and retrofitting
Workstream C's native motion primitives onto framer-motion/gsap.
