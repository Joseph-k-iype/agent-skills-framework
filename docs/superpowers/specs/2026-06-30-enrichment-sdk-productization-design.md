# Enrichment & SDK Productization — Design Spec

**Date:** 2026-06-30
**Branch:** `feat/eakso-phase-0-3` (continuing; baseline committed as 4 logical commits ending `1d64dea`)
**Status:** Approved — ready for implementation planning
**Builds on:** the now-committed SDK/API-keys/usage/analytics/marketplace-v2 subsystem and the OKF concept + FalkorDB graph projection.

## 1. Summary

Two related gaps turn the existing app into a richer, more usable product:

- **A — Knowledge/Taxonomy layer:** today `capabilities` is free-text with no canonical
  list, `sources` is not modeled at all, and concept hierarchy (`PARENT_OF`/`CHILD_OF`)
  is reserved in the ontology but unused. We add **graph-native, curated-open** controlled
  vocabularies for **capabilities and sources**, real **sub-concept** nesting, validation,
  seed taxonomies, and **faceted marketplace browse**.
- **B — SDK productization & DX:** the `eakso` Python SDK, API keys, and usage tracking
  already work, but the SDK isn't **downloadable** or documented in-app, and `usage_events`
  records `user_id` but **not** `api_key_id` — so per-key tracking is impossible. We make the
  SDK downloadable with in-app docs + a prefilled snippet, add **per-key usage attribution**,
  and add a **"test your key" playground**.

"Deep edge-case testing" is the quality bar applied across both, not a separate project.

## 2. Decisions (locked with user)

- **Scope:** one combined spec covering A + B, built as separable reviewable slices.
- **Reference-data model:** **graph-native, curated-open** — capabilities & sources are
  first-class FalkorDB nodes (reuse the reserved `Capability` label; add a `Source` label),
  seeded with a canonical hierarchical taxonomy. Concepts link via typed edges. A term not in
  the canonical set is **auto-created as `proposed` and linked — never rejected** — and
  surfaced to admins for curation.
- **Sub-concepts:** **generic parent-child** (`PARENT_OF`/`CHILD_OF`), author-labeled, with
  cycle prevention.
- **SDK delivery:** serve the **built artifact** (sdist/wheel) from an endpoint + in-app
  **docs/quickstart** page + a **prefilled snippet** (skill id baked in; API key entered at
  runtime, never embedded).
- **SDK languages:** **Python only** this phase (TypeScript is a later phase).

## 3. Existing ground truth (verified)

- Concept lives in git (markdown source) + FalkorDB (projection); **no Postgres concept model**.
  `capabilities: list[str]` exists, free-text. `concept_service._KNOWN` gates known frontmatter
  keys. Indexing upserts the `Concept` node and `REFERENCES` edges (`concept_graph_repo.py`,
  `graph/cypher/concept.py`).
- Ontology (`graph/ontology.py`) reserves `Capability` label and `PARENT_OF`/`CHILD_OF`,
  `USES`, `DEPENDS_ON` relationship types (unused today).
- Workspace-graph code already implements **folder cycle detection** — reuse that pattern for
  concept-hierarchy cycle prevention.
- API keys: `sk_live_…`, SHA256-hashed, enforced via `require_api_key` (`api/deps.py`).
  `usage_events` has `listing_id`, `user_id` (nullable), `kind`, `meta` (JSONB) — **no
  `api_key_id`**. `MarketplaceService.fetch_skill`/`report_usage` write usage via
  `marketplace_repo.add_usage`.
- SDK is a real package at **`sdk/python/`** (root, not `backend/`): `eakso/client.py`
  (httpx `Client` + `Skill.apply`), `pyproject.toml` (hatchling), `tests/test_client.py`.
- Marketplace listing (`models/marketplace.py`) mirrors concept metadata at publish; public
  catalog served by `MarketplaceService.public_list` / `public.py` router.

## 4. Part A — Knowledge/Taxonomy layer

### 4.1 Reference-data graph model

Two FalkorDB node labels: `Capability` (activate reserved) and `Source` (new). Term node props:
`key` (slug, unique per label), `label`, `description`, `status` (`canonical` | `proposed`),
`created_at`, `updated_at`. Hierarchy via `(:Capability)-[:PARENT_OF]->(:Capability)` (same for
`Source`). Terms are workspace-agnostic (global taxonomy), keyed by `key`.

`graph/cypher/taxonomy.py` (new): UPSERT_TERM, SET_PARENT, LIST_TREE (per label), LIST_PROPOSED,
PROMOTE (set status canonical), MERGE_TERM (repoint edges from alias → target, delete alias).
`repositories/taxonomy_repo.py` wraps these; `services/taxonomy_service.py` holds curation logic.

### 4.2 Seed taxonomy

`db/seed_taxonomy.py` — `seed_taxonomy(graph)` idempotent (skip if a known canonical root exists).
Capabilities (hierarchical, e.g.): `extraction` (→ `extraction.table`, `extraction.entity`),
`transformation` (→ `.normalize`, `.geocode`), `enrichment`, `validation`, `classification`,
`generation`, `redaction`. Sources: `file` (→ `file.csv`, `file.pdf`), `database` (→ `database.postgres`),
`api` (→ `api.rest`), `stream` (→ `stream.kafka`), `web` (→ `web.scrape`). Wired into the existing
startup seed path alongside `seed_marketplace`.

### 4.3 Concept schema additions

Add `sources: list[str]` everywhere `capabilities` lives: `okf/concept.py` dataclass + parser,
`concept_service._KNOWN`, `schemas/concept.py` (Create/Update/Out/Summary), graph node props in
`concept_graph_repo.upsert_concept` + `cypher/concept.py`. Add `parent_path: str | None` to
ConceptCreate/Update/Out.

### 4.4 Concept → reference edges (curated-open)

At index time (`index_service` / `concept_service` reindex), for each capability/source in
frontmatter: ensure the term node exists (auto-create `status=proposed` if unknown), then
`MERGE (c:Concept)-[:USES]->(:Capability)` / `MERGE (c:Concept)-[:DERIVED_FROM]->(:Source)`.
Clear-and-rebuild these edges on reindex (mirror the existing `CLEAR_REFERENCES_FROM` pattern).
Unknown term → proposed node + link, **never an error**.

### 4.5 Sub-concept hierarchy

`(:Concept)-[:PARENT_OF]->(:Concept)` set from `parent_path` (parent concept in the same
workspace). **Cycle prevention:** before linking, reject if the proposed parent is the concept
itself or a descendant of it (reuse workspace-graph cycle-detection approach) → `400` with a
clear message, no partial edge written. Extend NEIGHBORHOOD / WORKSPACE_GRAPH queries to include
`PARENT_OF` (parent + children) and `USES`/`DERIVED_FROM` neighbors.

### 4.6 Reference-data API + curation

New `routers/taxonomy.py` under `/taxonomy`:
- `GET /taxonomy/capabilities` → tree; `GET /taxonomy/sources` → tree. Auth `skill:read`.
  (For editor pickers + marketplace facets.)
- `GET /taxonomy/proposed` → flat list of `proposed` terms (both labels). Auth `taxonomy:manage`.
- `POST /taxonomy/{label}` → create canonical term `{key, label, description, parent_key?}`.
- `POST /taxonomy/{label}/{key}/promote` → set `proposed` → `canonical`.
- `POST /taxonomy/{label}/{key}/merge` `{into_key}` → repoint concept edges to `into_key`, delete alias.
  All mutations require `taxonomy:manage`.

Add `taxonomy:manage` to the RBAC catalog (`auth/rbac.py`), granted to `admin`.

### 4.7 Faceted marketplace browse

Mirror `capabilities`/`sources` onto `MarketplaceListing` (two JSONB columns) at publish, like
existing `tags`. Migration adds the columns. `marketplace_repo.list` / `public_list` accept
optional `capability` / `source` filters (match against the JSONB arrays). Public router gains the
query params; frontend marketplace page gains facet controls (Swiss styling — restrained, red tick
for active, consistent with the existing hero/filters).

### 4.8 Editor pickers

`ConceptEditorPage`: capability & source autocomplete pickers populated from the `/taxonomy` trees
(free entry allowed → becomes `proposed` on save), and a parent-concept selector (search existing
concepts in the workspace). New small components under `features/concepts/` (kept focused).

## 5. Part B — SDK productization & DX

### 5.1 Per-key usage tracking

Migration: add `api_key_id UUID NULL` (FK → `api_keys.id`, indexed) to `usage_events`.
`ApiKeyService.authenticate` returns `(user_id, api_key_id)`; `require_api_key` exposes the key id
(extend `CurrentUser` with optional `api_key_id`, or return a small auth result). SDK endpoints
(`routers/sdk.py`) pass `api_key_id` into `marketplace_repo.add_usage` (new optional param;
existing callers pass `None`). Owner-scoped `GET /api-keys/{id}/usage` → `{total, last_used_at,
by_kind, by_skill, recent[]}`; `404`/`403` if the key isn't the caller's. API-keys settings UI
shows per-key volume + last-used + recent activity.

### 5.2 Downloadable SDK + docs

`GET /sdk/download` → `FileResponse` of the built `eakso` artifact (sdist/wheel) with a
`X-Checksum-SHA256` header; if no artifact is present, **honest `503` `{ok:false, reason}`**, never
a fake file. Build step: produce the artifact into a known path (`sdk/python/dist/`) as part of
container build / a make target; the endpoint serves whatever is there. In-app **SDK docs page**
(`features/sdk/` or `features/settings/`): rendered via `MarkdownPreview` — install (from the
downloaded artifact), create-key → fetch → apply quickstart, `Client`/`Skill` API reference, and a
**snippet prefilled with a chosen skill id** (key read from env/`EAKSO_API_KEY` at runtime, never
embedded). Docs content authored in-repo.

### 5.3 "Test your key" playground

In-app UI: pick one of your keys + a skill → "Run" issues a **real** request to `/sdk/skill/{id}`
with the key → render the response (`system_prompt`/`content`) **and** confirm the usage event was
recorded (it appears in that key's `/api-keys/{id}/usage`). A revoked/invalid key surfaces the
**real `401`** from the SDK endpoint — no faked success. Honest end-to-end exercise of
key → fetch → track.

## 6. Roles / permissions

- Add `taxonomy:manage` (admin) to `auth/rbac.py`.
- Per-key usage and the playground are owner-scoped (a user sees only their own keys' usage).

## 7. Data flow

Author sets capabilities/sources/parent in the editor → save → reindex upserts the `Concept`
node + `USES`/`DERIVED_FROM`/`PARENT_OF` edges (auto-creating `proposed` terms) → publish mirrors
capabilities/sources onto the listing → marketplace facets filter on them.
SDK call: client → `/sdk/skill/{id}` with `sk_live_…` → `require_api_key` yields
`(user_id, api_key_id)` → `fetch_skill` writes a `usage_event` carrying `api_key_id` →
`/api-keys/{id}/usage` and the playground surface it.

## 8. Error handling

- Curated-open: unknown capability/source → `proposed` node + link, success — never `4xx`.
- Concept hierarchy cycle (self/descendant parent) → `400`, no partial edge.
- Missing SDK artifact → honest `503 {ok:false, reason}`.
- Per-key usage / playground for a key you don't own → `403`/`404`.
- Playground with a revoked/invalid key → surfaces the real `401` from the SDK endpoint.
- Taxonomy merge into a nonexistent target → `400`.

## 9. Testing (deep edge-case bar)

**Backend** (`uv run --python 3.12 pytest`):
- Seed idempotency (run twice → same node count); hierarchy parent links; tree listing.
- Curated-open: unknown term auto-creates `proposed` + links (no error); promote flips status;
  merge repoints concept edges and deletes the alias.
- Concept `sources` round-trips through frontmatter ↔ schema ↔ graph.
- Sub-concept: link parent; **reject self-parent and descendant-parent cycles** (no partial edge);
  neighborhood includes parent/children + capability/source neighbors.
- Faceted listing filters (capability, source, combined; empty result).
- Per-key usage: `fetch`/`apply` attribute `api_key_id`; anonymous (no key) still writes a row with
  `api_key_id=NULL`; revoked key path; `/api-keys/{id}/usage` ownership (`403`/`404`).
- SDK download: serves artifact, content-type + checksum header; missing artifact → `503`.
- Playground endpoint: real fetch + usage recorded; invalid key → `401`.

**SDK package** (`sdk/python`): existing client tests stay green; add any new surface.

**Frontend** (vitest + RTL): capability/source pickers (autocomplete + free entry), parent
selector, marketplace facet filters, per-key usage panel, playground run + result render, SDK docs
page renders + download link present.

## 10. Build sequence (each a reviewable slice)

1. **Taxonomy graph foundation:** `Capability`/`Source` nodes, `cypher/taxonomy.py`,
   `taxonomy_repo`, `taxonomy_service`, `seed_taxonomy` + wiring, concept `sources` field end-to-end,
   `USES`/`DERIVED_FROM` edges with curated-open auto-create, `GET /taxonomy/{capabilities,sources}`.
2. **Sub-concept hierarchy:** `parent_path`, `PARENT_OF` edges, cycle prevention, neighborhood/
   workspace-graph extension.
3. **Curation + faceted browse + editor pickers:** `/taxonomy/proposed|create|promote|merge`,
   `taxonomy:manage` perm, listing capability/source JSONB columns + migration + filters, editor
   capability/source/parent pickers.
4. **Per-key usage tracking:** `api_key_id` migration, thread through auth + SDK endpoints +
   `add_usage`, `GET /api-keys/{id}/usage`, settings UI per-key stats.
5. **SDK download + docs page + prefilled snippet:** build/serve artifact endpoint, in-app docs page.
6. **"Test your key" playground:** UI + wiring against the real SDK endpoint.
7. **Deep edge-case test pass + final whole-branch review.**

## 11. Out of scope (YAGNI)

- TypeScript/JS SDK (later phase).
- Publishing the SDK to PyPI / a private index (artifact download covers this phase).
- Free-text → taxonomy auto-suggestion via LLM (the editor offers the controlled list; no model).
- A full graph-visualization redesign (extend existing neighborhood views, don't rebuild).
- Cross-workspace taxonomy scoping / per-workspace private vocabularies (taxonomy is global).
