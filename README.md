# EAKSO — Enterprise AI Knowledge & Skills Operating System

A knowledge-graph-native platform for authoring, organizing, evaluating and
sharing AI agent skills. Enterprise knowledge is ingested from **OKF** (Open
Knowledge Format) documents into **FalkorDB**, which is the single source of
truth for the workspace hierarchy, skills and semantic (vector) search.

This repository implements **Phases 0–3** of the platform: Foundation, Workspace,
Knowledge (OKF), and Skills. Later phases (Workflow Builder, Agents,
Evaluation/Governance, Marketplace, Analytics) are scaffolded.

## Architecture

```
React + Vite + Ant Design (themed)        ── frontend/  (Zustand, TanStack Query, React Flow)
        │  REST /api/v1  (envelope, JWT)
FastAPI + SQLAlchemy + Celery             ── backend/   (services / repositories / graph layers)
        ├── PostgreSQL  users, roles, sessions, audit, marketplace metadata
        └── FalkorDB    workspace tree, folders, skills, OKF docs, vector embeddings
OpenRouter                                 ── embeddings + chat (offline fallback when no key)
```

- **Data split:** PostgreSQL holds identity/audit/marketplace; FalkorDB is the
  source of truth for the graph (workspaces, folders, skills, OKF documents) and
  native vector embeddings — no external vector DB.
- **Layering:** business logic only in `services/`; ORM confined to
  `repositories/`; all Cypher goes through parametrized builders in
  `graph/cypher/`.
- **Auth:** LDAP with a hardcoded dev-admin fallback (`admin` / `admin`).
  Three-tier RBAC (consumer / developer / admin) enforced server-side.

## Prerequisites

- Docker (for Postgres + FalkorDB)
- [uv](https://docs.astral.sh/uv/) (Python 3.12) and Node 20+

## Quick start

```bash
cp .env.example .env          # set OPENROUTER_API_KEY for real semantic search (optional)

make data                     # start Postgres + FalkorDB (Docker images)
make install                  # backend (uv) + frontend (npm) deps
make migrate                  # apply Alembic migrations
make seed                     # roles, permissions, dev-admin

# in separate terminals:
make backend                  # FastAPI on :8000  (uvicorn via uv)
make frontend                 # Vite dev server on :5173
make worker                   # (optional) Celery worker for background OKF ingest
```

Open http://localhost:5173 and sign in as **admin / admin**.

Try it:
1. **Workspace** → create a workspace and nested folders; drag to reorganize.
2. **Knowledge Graph** → *Import OKF* with the absolute path to
   `scripts/seed_okf_sample`, then search (e.g. "how is revenue recognized").
3. **Skills** → create a skill in a folder, attach OKF references, publish a new
   version to see the lineage.

> Only Postgres and FalkorDB run as Docker images. FalkorDB (a Redis module)
> also serves Redis for Celery. Backend, Celery and the frontend run natively.

## Testing

```bash
make test            # backend pytest + frontend vitest
make test-backend    # pytest (unit + graph + integration against real FalkorDB)
make test-frontend   # vitest + RTL
make lint            # ruff + mypy + eslint
```

Graph and integration tests run against the live FalkorDB/Postgres started by
`make data`, using an isolated `eakso_test` graph that is reset per test.

## Layout

```
backend/app/
  api/        routers (v1), deps (RBAC), error envelope
  auth/       LDAP seam, dev-admin, JWT, RBAC catalog
  graph/      FalkorDB client, ontology, index bootstrap, cypher/, vector search
  okf/        OKF parser + linker (pure)
  services/   workspace, okf, knowledge, skill, auth, audit
  repositories/  PostgreSQL repos + *_graph_repo (FalkorDB)
  models/ schemas/ events/ tasks/ llm/
frontend/src/
  app/        theme, layouts (sidebar / top-nav), providers
  features/   auth, dashboard, workspace, knowledge, skills
  shared/     api client, components ; stores/ (Zustand) ; router/
scripts/seed_okf_sample/   sample OKF knowledge set
```
