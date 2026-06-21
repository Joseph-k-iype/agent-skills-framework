# Frontend dashboard

A web UI and API for managing the Agent Skills Framework registry: browse skills,
inspect manifests, scaffold and publish new skills, install them, sync registry
sources, audit activity, and (optionally) explore a FalkorDB-backed knowledge
graph of skill capabilities and dependencies.

This package is **not** the skill framework itself — it's an operational
dashboard layered on top of the `skill_sdk` Python SDK and the filesystem
`registry/` that already exist at the repo root (see
[architecture.md](./architecture.md)). Every feature here reads from or
mutates that same registry; there's no separate data store.

## Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | FastAPI | `frontend/api/` |
| Backend language | Python 3.11+ | imports `skill_sdk` via `sys.path` insert, same pattern as the CLI |
| ASGI server | uvicorn | `--reload` in dev |
| Frontend framework | React 19 | function components + hooks only |
| Build tool | Vite 6 | dev server on `:5173`, proxies `/api` → `:8000` |
| Routing | react-router-dom v7 | client-side, lazy-loaded route chunks |
| Data fetching / cache | @tanstack/react-query v5 | all server state goes through `useQuery`/`useMutation` |
| Styling | Tailwind CSS v3 | utility classes, dark theme only |
| Icons | lucide-react | |
| Graph visualization | @xyflow/react v12 | the Knowledge Graph page |
| Code/YAML editor | @monaco-editor/react | read-only manifest preview in Create Skill |
| Frontend tests | Vitest + @testing-library/react + jsdom | |
| Backend tests | pytest + httpx (via FastAPI `TestClient`) | |

No database. State lives in: the filesystem registry (`registry/index.yaml` +
`registry/skills/<name>-<version>/`), an append-only JSONL audit log
(`registry/.audit.jsonl`), and a sandboxed scratch area (`workspace/`) for
scaffold/build/install operations.

## Architecture

```
frontend/
├── api/                      FastAPI backend
│   ├── main.py               app factory, CORS, router mounts, /api/health
│   ├── deps.py                shared RegistryClient singleton (auto_tag=False)
│   ├── security.py           workspace sandboxing + opt-in API-key gate
│   ├── audit.py              append-only JSONL audit log (read/record)
│   └── routes/
│       ├── dashboard.py      GET /api/dashboard/stats
│       ├── skills.py         skill CRUD, validate/verify, install, build, publish, scaffold, compliance
│       ├── registry.py       registry info, sources, add-source, sync
│       ├── graph.py          FalkorDB connect/register/query (optional)
│       ├── audit.py          GET /api/audit
│       └── deployments.py    GET /api/deployments
└── src/                      React frontend (Vite)
    ├── main.tsx               entry point, mounts <App/>
    ├── App.tsx                <AuthProvider> → <AppShell> → <ErrorBoundary> → <Suspense> → <Routes>
    ├── lib/
    │   ├── api.ts             typed fetch client, ApiError, X-API-Key header injection
    │   ├── types.ts           shared TS interfaces mirroring the backend's JSON shapes
    │   ├── auth.tsx            client-side role context (UX preview, not real authz — see security.md)
    │   └── utils.ts
    ├── components/
    │   ├── layout/            AppShell, Sidebar (role-filtered nav), TopBar (global search)
    │   ├── InstallModal.tsx   real install flow against POST /skills/{name}/install
    │   ├── RequireRole.tsx    <RequirePermission actions={[...]}> gate + fallback UI
    │   └── ErrorBoundary.tsx  class component catching render errors
    └── routes/                one file per page (see Features below)
```

### Request flow

Every data-fetching component uses TanStack Query against a small typed client
(`src/lib/api.ts`). There is no global Redux-style store — page state is local
`useState`, server state is cache-managed by React Query (keyed by endpoint,
e.g. `['skills']`, `['dashboard-stats']`, `['audit']`). Mutations invalidate the
relevant query keys on success so the UI reflects real backend state
immediately, with no optimistic/fake updates.

### Backend → SDK wiring

`api/deps.py` constructs one process-wide `RegistryClient` pointed at the
repo's real `registry/` directory (`auto_tag` forced `False` so the dashboard
never auto-creates git tags as a side effect of browsing). All route handlers
take that client via `Depends(get_registry)` and call straight into
`skill_sdk.registry`, `skill_sdk.validation`, `skill_sdk.hashing`,
`skill_sdk.versioning`, and `skill_sdk.adapter` — the same functions the CLI
uses (see [python-sdk.md](./python-sdk.md)). There is no parallel
reimplementation of registry logic in the API layer.

## Features (by route)

| Route | Page | What it does |
|---|---|---|
| `/` | Dashboard | Live stats (`total_skills`, `total_versions`, `sources_count`) from `GET /api/dashboard/stats`; recent-skills list sorted by version count; quick links to Create/Browse/Graph |
| `/skills` | Skill Catalog | Lists all registry skills (`GET /api/skills`); search filters by name; search term syncs with the `?q=` query param so links from TopBar work |
| `/skills/new` | Create Skill | 4-step wizard (Basic Info → Capabilities/Permissions → Dependencies/Triggers → Review) that builds a manifest object client-side, previews the frontmatter as YAML in a read-only Monaco editor, and can **download** the full `SKILL.md` (frontmatter + a generated stub body) or **scaffold it on the server** (`POST /api/skills/scaffold`), optionally publishing in the same call if the user has `skill:publish`. Gated behind `skill:create`. |
| `/skills/:name` | Skill Detail | Tabs for manifest (raw manifest file text, falling back to parsed JSON), documentation (the `SKILL.md` Markdown body, falling back to generated docs via `skill_sdk.adapter`), versions (SemVer-sorted), and dependencies, plus a Valid/Invalid badge from the validation API. Drives the Install modal. |
| `/registry` | Registry | Shows configured sources (local/git), lets you add a new source (`POST /api/registry/sources`, gated) and trigger a sync (`POST /api/registry/sync`, gated) — surfaces real `synced`/`errors` counts from the SDK's `sync_from_sources()`. |
| `/graph` | Knowledge Graph | Renders all registry skills as nodes in a radial layout via `@xyflow/react` using only local registry data (no FalkorDB required). If you connect to a running FalkorDB instance (`POST /api/graph/connect`), you unlock capability search and impact-analysis queries (`POST /api/graph/query`) and skill registration into the graph (`POST /api/graph/register`, gated). Degrades gracefully — no FalkorDB, no Redis, no crash, just the local-only view. |
| `/governance` | [Governance](#governance) | One-shot compliance table (`GET /api/skills/compliance`) — per-skill validity, permission/capability counts, and validation errors — plus a "Permissions by Resource" audit panel and a per-skill downstream "Show Impact" action. Gated to `governance`+ role in the sidebar. |
| `/deployments` | Deployments | Real deployment targets: the local registry (always present, with live skill count and path) plus one entry per configured source. Per-source skill counts are explicitly `null` (not fabricated) since the registry doesn't track per-source attribution. Last-sync timestamp is read from the audit log. |
| `/audit` | Audit Log | Full history from `GET /api/audit`, newest first, with relative timestamps and filters (all / publish / install / errors). Every mutating backend action (publish, install, scaffold, source-add, sync) appends here — nothing in this view is synthesized client-side. |
| `/settings` | Settings | Shows the real registry workspace path, the real `auto_tag` setting, and whether API-key auth is currently required — all read from `GET /api/registry`. Also hosts the role switcher, with an explicit warning that it's a client-side preview only. |
| `*` | Not Found | Catch-all 404 with a link back to the Dashboard. |

### Governance

Two pieces beyond the base compliance table, both gated behind
`useAuth().can('skill:audit')`:

- **Permissions by Resource** — a local-first audit panel, built entirely
  client-side from `permission_details` (the full `{resource, actions}[]`
  list now returned per skill by `GET /api/skills/compliance`, not just a
  count). Grouped by `resource` so you can see every skill that requests a
  given resource and which actions it asked for, with zero FalkorDB
  dependency.
- **Show Impact** — a per-row action that lazily fetches
  `GET /api/skills/{name}/impact`, which computes the **downstream** skills
  that depend on this one (directly or transitively) purely from the local
  registry's declared `dependencies.skills` — no FalkorDB required. This is
  deliberately a different traversal from the FalkorDB `find_impact`
  Cypher query exposed via `POST /api/graph/query` with `impact_id`, which
  walks **forward** dependencies (what the skill itself depends on) and is
  unchanged because the CLI's `--impact-id` flag and its docs depend on that
  direction. Use `/skills/{name}/impact` to answer "what breaks if I change
  this skill," and `impact_id` to answer "what does this skill depend on."

If a FalkorDB instance is connected, permissions are also queryable there
(`find_skills_by_permission`, surfaced via the Knowledge Graph page's "By
Permission" mode and `POST /api/graph/query` with `permission_resource`) —
but the Governance panel itself never needs it.

### Role-based UI gating (client-side only)

`src/lib/auth.tsx` defines five roles (`admin`, `developer`, `consumer`,
`governance`, `viewer`) with a permission map and a hierarchy. `useAuth().can(...)`
and `<RequirePermission>` hide or disable controls — e.g. only `developer`/`admin`
can scaffold a skill, only roles with `skill:install` see an enabled Install
button. **This affects which buttons render, not what the server accepts.**
See [security.md](./security.md).

## API surface

All routes are mounted under `/api`. Mutating routes are marked **🔒** —
gated by `require_api_key` when `SKILLS_API_KEY` is set (see below).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness check |
| GET | `/api/dashboard/stats` | aggregate counts for the Dashboard |
| GET | `/api/skills` | `{name: {latest, versions, ids, locations}}` for every skill |
| GET | `/api/skills/compliance` | per-skill validity/permissions (count + full `permission_details`)/capabilities/errors in one call |
| GET | `/api/skills/{name}` | single skill's registry entry |
| GET | `/api/skills/{name}/manifest` | parsed manifest + raw file text |
| GET | `/api/skills/{name}/doc?format=markdown\|json` | generated docs via `skill_sdk.adapter` |
| GET | `/api/skills/{name}/versions` | SemVer-ascending version list + ids |
| GET | `/api/skills/{name}/impact` | `{downstream: [...], count}` — registry-only transitive dependents, see [Governance](#governance) |
| POST | `/api/skills/{name}/validate` | structural validation errors + lint warnings |
| POST | `/api/skills/{name}/verify?version=` | recomputes and checks the content-addressed ID |
| POST 🔒 | `/api/skills/{name}/install` | installs into `workspace/installed/<name>` (or a custom sandboxed target); body: `{version?, target?, verify}` |
| POST 🔒 | `/api/skills/build` | validates + computes the would-be skill ID for a workspace path; body: `{path}` |
| POST 🔒 | `/api/skills/publish` | publishes a workspace skill dir into the registry; body: `{path, force}`. Also triggers best-effort FalkorDB sync if `SKILLS_GRAPH_HOST` is set — see [Configuration](#configuration-environment-variables) |
| POST 🔒 | `/api/skills/scaffold` | writes a new skill dir (manifest + entry stub + extra files) into the workspace, validates it, optionally publishes; body: `{manifest, files?, publish?, force?}` |
| GET | `/api/registry` | sources, skill count, `auto_tag`, `workspace`, `auth_required` |
| GET | `/api/registry/sources` | raw source list |
| POST 🔒 | `/api/registry/sources` | add a local or git source (paths sandboxed) |
| POST 🔒 | `/api/registry/sync` | pull latest versions from all sources; returns `{synced, skills, errors}` |
| GET | `/api/audit?limit=200` | newest-first audit entries |
| GET | `/api/deployments` | local registry + configured sources as deployment targets |
| POST | `/api/graph/connect` | test a FalkorDB connection |
| POST 🔒 | `/api/graph/register` | register a skill manifest into FalkorDB (capabilities, dependencies, and permissions) |
| POST | `/api/graph/query` | query by `capability`, `impact_id` (forward dependencies), or `permission_resource` |

Reads are always open, even when an API key is configured — put the dashboard
behind your own gateway if reads must also be protected (see
[security.md](./security.md)).

## How to run

Requires Python 3.11+ and Node 18+.

```bash
cd frontend

# 1. Backend deps (installs into your active Python env)
pip install -r api/requirements.txt
# optional, for backend tests:
pip install pytest httpx

# 2. Frontend deps
npm install

# 3a. Run both backend + frontend together
npm run dev:all

# 3b. ...or run them separately, in two terminals
npm run api    # uvicorn on :8000, --reload
npm run dev    # vite on :5173, proxies /api -> :8000
```

Open `http://localhost:5173`. The Vite dev server proxies any `/api/*` request
to the FastAPI backend, so the frontend never needs to know the backend's host.

The backend finds `skill_sdk` the same way the CLI does — by inserting
`sdks/python` onto `sys.path` at import time (`api/main.py`). No installation
step, no virtualenv requirement beyond the two pip packages above.

### Production build

```bash
npm run build      # tsc -b && vite build -> dist/
npm run preview    # serve the production build locally
```

Serve `dist/` behind the same origin as the FastAPI app (or configure
`allow_origins` in `api/main.py` for a different origin) and run the backend
with a production ASGI server (e.g. `uvicorn api.main:app --host 0.0.0.0`).

### Tests

```bash
# Backend (from frontend/, with the repo's Python SDK on the path)
PYTHONPATH=../sdks/python:.. python -m pytest api/tests

# Frontend
npm test            # vitest run (single pass)
npm run test:watch  # vitest watch mode
```

### Configuration (environment variables)

| Variable | Default | Effect |
|---|---|---|
| `SKILLS_WORKSPACE` | `<repo>/workspace` | Sandbox root for scaffold/build/publish/install/source paths. Created automatically. |
| `SKILLS_API_KEY` | unset | When set, mutating endpoints require `X-API-Key: <value>` or `Authorization: Bearer <value>`. Unset = open (local dev). |
| `VITE_API_KEY` | unset | Build-time value the frontend attaches as `X-API-Key` on every request. Must match `SKILLS_API_KEY` server-side. |
| `SKILLS_GRAPH_HOST` | unset | When set, `deps.py` constructs a `FalkorDBConnector` and passes it into the shared `RegistryClient`, so every `publish`/`scaffold(...,publish=True)` call best-effort syncs to FalkorDB afterward. Unset = no graph dependency at all (default). |
| `SKILLS_GRAPH_PORT` | `6379` | Port for the above, only read when `SKILLS_GRAPH_HOST` is set. |

## Security model

See [security.md](./security.md) for the full writeup. Summary, since this
dashboard is built to be safely exposed as a **shared/hosted** service rather
than assumed to run only on localhost:

- **Path sandboxing**: every endpoint that accepts a filesystem path
  (`build`, `publish`, `scaffold`, install `target`, local registry `sources`,
  `graph/register`) resolves it through `resolve_in_workspace()`, which
  rejects traversal (`..`) and any absolute path outside the workspace root
  with HTTP 400.
- **Opt-in API-key gate**: mutating endpoints check a single shared secret
  (`SKILLS_API_KEY`) when configured; reads are always open.
- **Known, documented gap**: the frontend's role switcher (`/settings`,
  `lib/auth.tsx`) is a **client-side UX preview only**. It controls which
  buttons render — it is not consulted by the server and is not a real
  per-user authorization boundary. There is exactly one shared API key, not
  per-user credentials. For real multi-tenant authz, put this behind an
  authenticating reverse proxy / identity provider that maps identities to
  permissions server-side. This is surfaced explicitly in the Settings page,
  not hidden.
- **Audit log**: every mutating action (publish, install, scaffold,
  source-add, sync) is appended to `registry/.audit.jsonl` regardless of
  success/failure, with file locking for safe concurrent writers.

## Honesty notes (no fabricated data)

Earlier iterations of a few pages synthesized plausible-looking demo data
(fake timestamps, fake "Auto-tag: Enabled" status, fake per-source skill
counts). All of that has been replaced with real backend-derived values; where
a real value genuinely isn't trackable yet (e.g. which skills came from which
configured source), the UI shows `null`/"—" rather than inventing a number.
