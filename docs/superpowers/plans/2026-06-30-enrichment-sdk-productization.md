# Enrichment & SDK Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add graph-native controlled vocabularies (capabilities + sources), sub-concept hierarchy, and faceted browse; and productize the existing `eakso` SDK with per-key usage tracking, a downloadable artifact + in-app docs, and a "test your key" playground.

**Architecture:** Reference data is modeled as first-class FalkorDB nodes (`Capability`, `Source`) with a hierarchical `PARENT_OF` tree, linked from `Concept` nodes via `USES`/`DERIVED_FROM` edges built at index time (curated-open: unknown terms auto-create as `proposed`, never reject). Sub-concepts use `Concept-[:PARENT_OF]->Concept` with cycle prevention reusing the existing workspace-graph approach. SDK productization extends the already-working API-key/usage subsystem: add `api_key_id` to `usage_events`, serve the built SDK artifact, and add owner-scoped per-key usage + a real end-to-end playground.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, PostgreSQL, FalkorDB (Cypher), pydantic; React + TypeScript + Vite + Ant Design v5, TanStack Query, vitest + RTL. Backend tests: `cd backend && uv run --python 3.12 pytest`. Frontend checks: `npx tsc -b`, `npm run build`, `npx vitest run`.

## Global Constraints

- **Curated-open, never reject:** a capability/source term not in the canonical set is auto-created as a node with `status="proposed"` and linked. Indexing/saving a concept with unknown terms MUST succeed (no 4xx).
- **Term `status`** is exactly one of `"canonical"` | `"proposed"` (string literals).
- **Node labels:** `Capability` (reuse the label already reserved in `graph/ontology.py`), `Source` (new — add to the NodeLabel enum). **Relationship types:** `USES` (Concept→Capability, already reserved), `DERIVED_FROM` (Concept→Source, add to RelType enum), `PARENT_OF` (Capability→Capability, Source→Source, and Concept→Concept — already reserved).
- **Term node key:** `key` is a slug, unique per label; hierarchy keys use dot notation (e.g. `extraction.table`). Terms are global (not workspace-scoped).
- **Concept hierarchy cycle** (self-parent or descendant-as-parent) → HTTP `400` with a clear message, no partial edge written.
- **Per-key tracking:** every SDK-authenticated usage event records `api_key_id`; non-SDK/anonymous usage records `api_key_id = NULL`. The column is nullable.
- **API keys are never embedded** in generated SDK snippets — the snippet reads the key from `EAKSO_API_KEY` at runtime.
- **Missing SDK artifact** → honest `503 {ok: false, reason: <str>}`, never a fabricated/empty file.
- **Ownership:** per-key usage and the playground are owner-scoped; another user's key → `404` (do not leak existence).
- **Swiss design system unchanged** for any new frontend (palette from `frontend/src/app/theme/tokens.ts`; Tesla Red `#E82127` only as a functional marker; hairline borders, 4px radius, no shadows; monospace for data/SHA). New facet controls match the existing marketplace hero/filter styling.
- **Permissions:** add `taxonomy:manage` to `backend/app/auth/rbac.py`, granted to `admin` only. Read endpoints use `skill:read`.
- Every task is TDD: failing test → run-red → implement → run-green → commit. Frequent commits.

---

## File Structure (decomposition)

**Backend — new files:**
- `backend/app/graph/cypher/taxonomy.py` — Cypher query strings for term upsert/parent/list/promote/merge (mirrors the style of `graph/cypher/concept.py`).
- `backend/app/repositories/taxonomy_repo.py` — thin async wrapper over the graph client running the taxonomy Cypher (mirrors `repositories/concept_graph_repo.py`).
- `backend/app/services/taxonomy_service.py` — taxonomy read + curation logic.
- `backend/app/db/seed_taxonomy.py` — `seed_taxonomy(graph)` idempotent canonical seed (mirrors `db/seed_marketplace.py`).
- `backend/app/api/v1/routers/taxonomy.py` — `/taxonomy` router.
- `backend/app/schemas/taxonomy.py` — pydantic models for terms / trees / curation requests.
- Tests: `backend/tests/integration/test_taxonomy_graph.py`, `test_taxonomy_seed.py`, `test_taxonomy_api.py`, `test_concept_references.py`, `test_concept_hierarchy.py`, `test_marketplace_facets.py`, `test_per_key_usage.py`, `test_sdk_download.py`.

**Backend — modified files:**
- `backend/app/graph/ontology.py` — add `Source` label, `DERIVED_FROM` rel type.
- `backend/app/okf/concept.py` — parse `sources`.
- `backend/app/schemas/concept.py` — add `sources`, `parent_path`.
- `backend/app/services/concept_service.py` — `_KNOWN` += `sources`; pass through `sources`/`parent_path`.
- `backend/app/services/index_service.py` (+ `concept_graph_repo.py`, `cypher/concept.py`) — write `sources` prop, build `USES`/`DERIVED_FROM`/`PARENT_OF` edges, extend neighborhood/workspace-graph queries.
- `backend/app/models/usage_event.py` + new migration — add `api_key_id`.
- `backend/app/services/api_key_service.py`, `backend/app/api/deps.py`, `backend/app/api/v1/routers/sdk.py`, `backend/app/repositories/marketplace_repo.py` — thread `api_key_id`.
- `backend/app/api/v1/routers/api_keys.py` — add `GET /api-keys/{id}/usage`.
- `backend/app/models/marketplace.py` + new migration, `backend/app/repositories/marketplace_repo.py`, `backend/app/api/v1/routers/public.py` — listing capability/source columns + facet filters.
- `backend/app/auth/rbac.py` — `taxonomy:manage`.

**Frontend — new files:**
- `frontend/src/features/concepts/components/TaxonomyPicker.tsx` — capability/source autocomplete (free entry allowed).
- `frontend/src/features/concepts/components/ParentConceptSelect.tsx` — parent selector.
- `frontend/src/features/sdk/pages/SdkDocsPage.tsx` + `frontend/src/features/sdk/api/sdkApi.ts` — docs page + download.
- `frontend/src/features/settings/components/KeyUsagePanel.tsx` — per-key usage.
- `frontend/src/features/sdk/pages/PlaygroundPage.tsx` — test-your-key playground.
- Vitest specs alongside each under `__tests__/`.

**Frontend — modified files:**
- `frontend/src/features/concepts/pages/ConceptEditorPage.tsx` — mount the pickers + parent select.
- `frontend/src/features/marketplace/pages/MarketplacePage.tsx` — facet controls.
- `frontend/src/features/settings/...` (API keys page) — mount `KeyUsagePanel`.
- `frontend/src/app/layouts/nav.ts` + `frontend/src/router/index.tsx` — routes for SDK docs + playground.

---

## Task 1: Taxonomy graph layer (cypher + repo + service)

**Files:**
- Create: `backend/app/graph/cypher/taxonomy.py`, `backend/app/repositories/taxonomy_repo.py`, `backend/app/services/taxonomy_service.py`
- Modify: `backend/app/graph/ontology.py` (add `Source` to NodeLabel, `DERIVED_FROM` to RelType)
- Test: `backend/tests/integration/test_taxonomy_graph.py`

**Interfaces:**
- Consumes: the graph client used by `concept_graph_repo.py` (read that file first to copy the exact client acquisition + `.query(cypher, params)` call style and the result-unpacking helpers).
- Produces:
  - `TaxonomyRepository(graph)` with async methods:
    - `upsert_term(label: str, key: str, term_label: str, description: str | None, status: str, parent_key: str | None) -> dict` — MERGE term node by (label, key); set props; if `parent_key`, MERGE `(parent)-[:PARENT_OF]->(child)`.
    - `get_term(label: str, key: str) -> dict | None`
    - `list_tree(label: str) -> list[dict]` — all terms of a label, each with its `parent_key` (caller assembles the tree).
    - `list_proposed() -> list[dict]` — terms across both labels with `status="proposed"`.
    - `promote(label: str, key: str) -> dict | None` — set `status="canonical"`.
    - `merge_term(label: str, key: str, into_key: str) -> bool` — repoint `(:Concept)-[r:USES|DERIVED_FROM]->(alias)` to `into_key`, delete alias node; returns False if `into_key` missing.
  - `TaxonomyService(graph)` wrapping the repo with: `tree(label)`, `proposed()`, `create(label, key, label_text, description, parent_key)`, `promote(label, key)`, `merge(label, key, into_key)`. `label` validated to `{"Capability","Source"}` (raise `ValueError` otherwise → router maps to 400).

- [ ] **Step 1: Read the patterns.** Read `backend/app/repositories/concept_graph_repo.py` and `backend/app/graph/cypher/concept.py` in full. Copy the graph-client acquisition, parameter-passing, and result-row unpacking idioms exactly. Note `ts` timestamp formatting (ISO 8601) used in `upsert_concept`.

- [ ] **Step 2: Write the failing test** `backend/tests/integration/test_taxonomy_graph.py`:

```python
import pytest
from app.repositories.taxonomy_repo import TaxonomyRepository

pytestmark = pytest.mark.asyncio

async def test_upsert_and_tree(graph):  # `graph` fixture: reuse the existing FalkorDB fixture (grep tests/ for it)
    repo = TaxonomyRepository(graph)
    await repo.upsert_term("Capability", "extraction", "Extraction", None, "canonical", None)
    await repo.upsert_term("Capability", "extraction.table", "Table extraction", None, "canonical", "extraction")
    tree = await repo.list_tree("Capability")
    keys = {t["key"]: t.get("parent_key") for t in tree}
    assert keys["extraction"] is None
    assert keys["extraction.table"] == "extraction"

async def test_unknown_term_proposed_then_promote(graph):
    repo = TaxonomyRepository(graph)
    await repo.upsert_term("Source", "weird.src", "Weird", None, "proposed", None)
    proposed = await repo.list_proposed()
    assert any(t["key"] == "weird.src" and t["status"] == "proposed" for t in proposed)
    await repo.promote("Source", "weird.src")
    t = await repo.get_term("Source", "weird.src")
    assert t["status"] == "canonical"
```

- [ ] **Step 3: Run it (RED).** `cd backend && uv run --python 3.12 pytest tests/integration/test_taxonomy_graph.py -v` → FAIL (module missing). If the `graph` fixture name differs, grep `tests/` for the existing FalkorDB fixture and use it.

- [ ] **Step 4: Implement** `cypher/taxonomy.py` (query strings), `taxonomy_repo.py`, ontology enum additions. Term node MERGE keyed on `{FalkorDB-label, key}`; store props `key,label,description,status,created_at,updated_at`. `PARENT_OF` between same-label terms.

- [ ] **Step 5: Run it (GREEN)** + graph/integration suite: `cd backend && uv run --python 3.12 pytest tests/integration/test_taxonomy_graph.py tests/graph -v`.

- [ ] **Step 6: Add `TaxonomyService`** with label validation (raise `ValueError` for unknown label) — covered via the API task. Commit.

```bash
git add backend/app/graph/cypher/taxonomy.py backend/app/repositories/taxonomy_repo.py backend/app/services/taxonomy_service.py backend/app/graph/ontology.py backend/tests/integration/test_taxonomy_graph.py
git commit -m "feat(taxonomy): graph layer for capability/source terms (upsert, tree, proposed, promote, merge)"
```

---

## Task 2: Seed canonical taxonomy + startup wiring

**Files:**
- Create: `backend/app/db/seed_taxonomy.py`, `backend/tests/integration/test_taxonomy_seed.py`
- Modify: the startup seed path (read `backend/app/db/seed_marketplace.py` and find where it's invoked — likely `backend/app/main.py` lifespan or `backend/app/db/seed.py`; wire `seed_taxonomy` beside it)

**Interfaces:**
- Consumes: `TaxonomyRepository.upsert_term` (Task 1).
- Produces: `async def seed_taxonomy(graph) -> int` returning the count of canonical terms ensured; idempotent. Module-level `CANONICAL: dict[str, list[tuple[str, str | None]]]` mapping label → `(key, parent_key)` pairs.

**Canonical seed (exact):**
- Capabilities: `extraction`(None), `extraction.table`(extraction), `extraction.entity`(extraction), `transformation`(None), `transformation.normalize`(transformation), `transformation.geocode`(transformation), `enrichment`(None), `validation`(None), `classification`(None), `generation`(None), `redaction`(None).
- Sources: `file`(None), `file.csv`(file), `file.pdf`(file), `database`(None), `database.postgres`(database), `api`(None), `api.rest`(api), `stream`(None), `stream.kafka`(stream), `web`(None), `web.scrape`(web).
- `label` (display) = title-cased last dot-segment; `description=None`; `status="canonical"`.

- [ ] **Step 1: Write the failing test** `test_taxonomy_seed.py`:

```python
import pytest
from app.db.seed_taxonomy import seed_taxonomy
from app.repositories.taxonomy_repo import TaxonomyRepository

pytestmark = pytest.mark.asyncio

async def test_seed_idempotent(graph):
    n1 = await seed_taxonomy(graph)
    n2 = await seed_taxonomy(graph)
    assert n1 == n2 and n1 >= 22
    caps = await TaxonomyRepository(graph).list_tree("Capability")
    assert {t["key"] for t in caps} >= {"extraction", "extraction.table", "transformation.geocode"}
    assert all(t["status"] == "canonical" for t in caps)
```

- [ ] **Step 2: Run it (RED).** `cd backend && uv run --python 3.12 pytest tests/integration/test_taxonomy_seed.py -v`.
- [ ] **Step 3: Implement** `seed_taxonomy` over `CANONICAL` (parents before children — lists above are ordered). Idempotent via MERGE.
- [ ] **Step 4: Run it (GREEN).**
- [ ] **Step 5: Wire into startup** beside `seed_marketplace`; run the full integration suite to confirm boot is clean.
- [ ] **Step 6: Commit.** `git commit -m "feat(taxonomy): seed canonical capability/source taxonomy (idempotent) + startup wiring"`

---

## Task 3: Concept `sources` field + curated-open reference edges

**Files:**
- Modify: `backend/app/okf/concept.py` (parse `sources` like `capabilities`), `backend/app/schemas/concept.py` (`sources: list[str] = []` on Create/Update/Out/Summary; `parent_path: str | None = None` on Create/Update/Out — carry it here, wire the edge in Task 5), `backend/app/services/concept_service.py` (`_KNOWN += ("sources",)`; pass `sources`), `backend/app/graph/cypher/concept.py` + `backend/app/repositories/concept_graph_repo.py` (store `sources` prop; clear+rebuild `USES`/`DERIVED_FROM`), `backend/app/services/index_service.py` (build reference edges, auto-creating `proposed` terms).
- Test: `backend/tests/integration/test_concept_references.py`, plus extend `backend/tests/unit/test_concept_model.py`.

**Interfaces:**
- Consumes: `TaxonomyRepository.upsert_term`, `get_term` (Task 1).
- Produces: after indexing, `(:Concept {key})-[:USES]->(:Capability {key})` per `capabilities[]` and `(:Concept)-[:DERIVED_FROM]->(:Source)` per `sources[]`; unknown term → `upsert_term(label, term, title(term), None, "proposed", None)` then the edge.

- [ ] **Step 1: Unit test** in `tests/unit/test_concept_model.py` — a concept with `sources: [file.csv, weird]` in frontmatter parses to `concept.sources == ["file.csv", "weird"]` (mirror the existing capabilities parsing test).
- [ ] **Step 2: Integration failing test** `test_concept_references.py`:

```python
import pytest
pytestmark = pytest.mark.asyncio

async def test_unknown_capability_is_proposed_not_rejected(concept_service, graph):
    c = await concept_service.create(workspace_id=WS, payload=ConceptCreate(
        name="Edge", capabilities=["totally.new.cap"], sources=["file.csv"], body="x"))
    from app.repositories.taxonomy_repo import TaxonomyRepository
    t = await TaxonomyRepository(graph).get_term("Capability", "totally.new.cap")
    assert t is not None and t["status"] == "proposed"
    nbr = await graph_neighbors(graph, WS, c.path)   # inline helper: outgoing USES/DERIVED_FROM keys
    assert "totally.new.cap" in nbr["capabilities"] and "file.csv" in nbr["sources"]
```

(Use the concept_service / workspace fixtures from `tests/integration/test_concept_service.py`; copy their setup. Write the small `graph_neighbors` helper inline.)

- [ ] **Step 3: Run it (RED).**
- [ ] **Step 4: Implement.** In `index_service` reindex, after the existing concept upsert + REFERENCES rebuild, clear+rebuild `USES`/`DERIVED_FROM` from `capabilities`/`sources`, calling `upsert_term(..., status="proposed")` ONLY when `get_term` returns None (never downgrade a canonical term). Add `sources` to the concept node props + `cypher/concept.py` UPSERT_CONCEPT.
- [ ] **Step 5: Run it (GREEN)** + `tests/integration/test_index_projection.py` + `tests/unit/test_concept_model.py`.
- [ ] **Step 6: Commit.** `git commit -m "feat(concept): sources field + curated-open USES/DERIVED_FROM edges (unknown terms proposed)"`

---

## Task 4: `/taxonomy` read API

**Files:**
- Create: `backend/app/api/v1/routers/taxonomy.py`, `backend/app/schemas/taxonomy.py`, `backend/tests/integration/test_taxonomy_api.py`
- Modify: `backend/app/api/v1/router.py` (register `taxonomy.router` prefix `/taxonomy`)

**Interfaces:**
- Consumes: `TaxonomyService` (Task 1), the graph dependency, `require_permission("skill:read")` from `api/deps.py` (read `deps.py` for the exact dependency call style).
- Produces:
  - `GET /api/v1/taxonomy/capabilities` → `{terms: [{key, label, description, status, parent_key}]}` (flat; client builds tree).
  - `GET /api/v1/taxonomy/sources` → same shape.
  - Schema `TermOut`, `TaxonomyTreeOut`.

- [ ] **Step 1: Failing test** `test_taxonomy_api.py` — seed taxonomy, then `GET /taxonomy/capabilities` with a `skill:read` token returns 200 and includes `extraction` (`parent_key=None`) and `extraction.table` (`parent_key="extraction"`); without auth → 401. (Copy the auth-client fixture from `test_concepts_api.py` / `test_api_keys_sdk.py`.)
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** router + schemas; register in `router.py`.
- [ ] **Step 4: Run it (GREEN).**
- [ ] **Step 5: Commit.** `git commit -m "feat(taxonomy): GET /taxonomy/{capabilities,sources} read API"`

---

## Task 5: Sub-concept hierarchy (PARENT_OF + cycle prevention)

**Files:**
- Modify: `backend/app/services/concept_service.py` (accept `parent_path`; on save, set the parent edge), `backend/app/graph/cypher/concept.py` + `backend/app/repositories/concept_graph_repo.py` (SET_PARENT, CLEAR_PARENT, descendant check, extend NEIGHBORHOOD/WORKSPACE_GRAPH to return parent + children), `backend/app/api/v1/routers/concepts.py` (map cycle error → 400).
- Test: `backend/tests/integration/test_concept_hierarchy.py`

**Interfaces:**
- Consumes: concept upsert (existing), `parent_path` schema field (Task 3).
- Produces:
  - `concept_graph_repo.set_parent(workspace_id, child_path, parent_path) -> None` — raises a cycle error (REUSE the existing workspace-graph cycle exception/helper — read `tests/graph/test_workspace_graph.py` + the folder reparent code to find it) if `parent_path == child_path` or `parent_path` is a descendant of `child_path`.
  - `concept_graph_repo.clear_parent(workspace_id, child_path)` — drop existing incoming `PARENT_OF` before setting a new one.
  - Neighborhood result gains `parent: str | None` and `children: list[str]`.

- [ ] **Step 1: Failing test** `test_concept_hierarchy.py`:

```python
import pytest
pytestmark = pytest.mark.asyncio

async def test_set_parent_and_neighborhood(concept_service, graph):
    parent = await concept_service.create(workspace_id=WS, payload=ConceptCreate(name="OCR", body="x"))
    child = await concept_service.create(workspace_id=WS, payload=ConceptCreate(name="Invoice OCR", parent_path=parent.path, body="y"))
    nbr = await concept_service.neighborhood(WS, child.path)
    assert nbr["parent"] == parent.path
    nbrp = await concept_service.neighborhood(WS, parent.path)
    assert child.path in nbrp["children"]

async def test_self_and_descendant_parent_rejected(concept_service):
    a = await concept_service.create(workspace_id=WS, payload=ConceptCreate(name="A", body="x"))
    b = await concept_service.create(workspace_id=WS, payload=ConceptCreate(name="B", parent_path=a.path, body="y"))
    with pytest.raises(Exception):  # self-parent
        await concept_service.update(WS, a.path, ConceptUpdate(parent_path=a.path))
    with pytest.raises(Exception):  # descendant-as-parent
        await concept_service.update(WS, a.path, ConceptUpdate(parent_path=b.path))
```

- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** `set_parent`/`clear_parent` with descendant traversal (reuse the workspace-graph cycle approach), wire into `concept_service` create/update, extend the neighborhood query, map the cycle error to 400 in the concepts router.
- [ ] **Step 4: Run it (GREEN)** + `tests/graph` + `tests/integration/test_concept_service.py`.
- [ ] **Step 5: Commit.** `git commit -m "feat(concept): sub-concept PARENT_OF hierarchy with cycle prevention"`

---

## Task 6: Taxonomy curation API + `taxonomy:manage` permission

**Files:**
- Modify: `backend/app/auth/rbac.py` (add `taxonomy:manage` to the catalog + grant to `admin` — read the file to copy the exact catalog/grant structure), `backend/app/api/v1/routers/taxonomy.py` (add curation endpoints), `backend/app/schemas/taxonomy.py` (request models).
- Test: extend `backend/tests/integration/test_taxonomy_api.py`

**Interfaces:**
- Consumes: `TaxonomyService.proposed/create/promote/merge` (Task 1), `require_permission("taxonomy:manage")`.
- Produces:
  - `GET /taxonomy/proposed` → `{terms: [...]}` (admin).
  - `POST /taxonomy/{label}` body `TermCreate{key, label, description?, parent_key?}` → `TermOut` (admin).
  - `POST /taxonomy/{label}/{key}/promote` → `TermOut` (admin).
  - `POST /taxonomy/{label}/{key}/merge` body `{into_key}` → `{ok: true}`; missing `into_key` → 400.
  - Unknown `{label}` → 400 (service `ValueError`).

- [ ] **Step 1: Failing tests** — admin lists proposed, promotes a proposed term (status flips to canonical via a follow-up `GET`), and merge alias→target repoints a concept's edge; a consumer token → 403; unknown label → 400; merge into missing target → 400.
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** rbac entry, endpoints, schemas, `ValueError`→400 handler.
- [ ] **Step 4: Run it (GREEN)** + the full auth/rbac test file.
- [ ] **Step 5: Commit.** `git commit -m "feat(taxonomy): curation API (proposed/create/promote/merge) + taxonomy:manage perm"`

---

## Task 7: Faceted marketplace browse (listing columns + filters)

**Files:**
- Modify: `backend/app/models/marketplace.py` (add `capabilities`, `sources` JSONB columns, default `[]` — mirror the existing `tags` column), `backend/app/services/marketplace_service.py` (mirror concept `capabilities`/`sources` onto the listing at publish — find the publish/upsert path that already copies `tags`), `backend/app/repositories/marketplace_repo.py` (`list`/`public_list` accept `capability: str | None`, `source: str | None`, filter against the JSONB arrays — mirror the existing tag filter), `backend/app/api/v1/routers/public.py` (+ `marketplace.py`) (accept `capability`/`source` query params).
- Create: migration `backend/migrations/versions/<rev>_listing_capabilities_sources.py` (two JSONB columns, server_default `'[]'`), `backend/tests/integration/test_marketplace_facets.py`

**Interfaces:**
- Consumes: existing publish path, existing `tags` filter pattern.
- Produces: `MarketplaceListing.capabilities: list`, `.sources: list`; `public_list(..., capability=None, source=None)`.

- [ ] **Step 1: Write the migration** (read `migrations/versions/d2b3c4e5f6a7_api_keys_usage_events.py` for style; set `down_revision` to the current head — confirm via `cd backend && uv run --python 3.12 alembic heads`).
- [ ] **Step 2: Failing test** `test_marketplace_facets.py` — publish two listings with differing capabilities/sources; `public_list(capability="extraction")` returns only the matching one; combined `capability+source` filter; a no-match filter returns `[]`. (Copy publish fixtures from `tests/integration/test_marketplace_*`.)
- [ ] **Step 3: Run it (RED).** Apply the migration to the test DB first if the suite needs the column (`alembic upgrade head`).
- [ ] **Step 4: Implement** columns, publish mirroring, repo filters, router params.
- [ ] **Step 5: Run it (GREEN)** + `tests/integration/test_marketplace_insights.py`.
- [ ] **Step 6: Commit.** `git commit -m "feat(marketplace): capability/source facets on listings + filtered browse"`

---

## Task 8: Editor pickers + marketplace facet UI (frontend)

**Files:**
- Create: `frontend/src/features/concepts/components/TaxonomyPicker.tsx`, `frontend/src/features/concepts/components/ParentConceptSelect.tsx`, `frontend/src/features/concepts/api/taxonomyApi.ts`, `frontend/src/features/concepts/components/__tests__/TaxonomyPicker.test.tsx`.
- Modify: `frontend/src/features/concepts/pages/ConceptEditorPage.tsx` (mount pickers + parent select, wire to save payload `capabilities`/`sources`/`parent_path`), `frontend/src/features/marketplace/pages/MarketplacePage.tsx` (capability/source facet controls bound to query params), `frontend/src/features/marketplace/api/marketplaceApi.ts` (pass facet params).

**Interfaces:**
- Consumes: `GET /taxonomy/{capabilities,sources}` (Task 4), the existing `http`/`unwrap` client (`@/shared/api/client`).
- Produces: `<TaxonomyPicker kind="capability"|"source" value={string[]} onChange />` — AntD `Select mode="tags"` seeded from the taxonomy tree, free entry allowed; `<ParentConceptSelect value onChange />`.

- [ ] **Step 1: Vitest failing test** `TaxonomyPicker.test.tsx` — renders options from a mocked `/taxonomy/capabilities`, selects a canonical term, and allows a free term not in the list (value updates). Wrap in QueryClientProvider (copy the harness from `frontend/src/app/layouts/__tests__/PublicLayout.test.tsx`).
- [ ] **Step 2: Run it (RED).** `cd frontend && npx vitest run src/features/concepts/components/__tests__/TaxonomyPicker.test.tsx`.
- [ ] **Step 3: Implement** the components + api + mount in editor + marketplace facets (Swiss: restrained controls, red tick for active facet, consistent with the existing hero filters).
- [ ] **Step 4: Run** `npx vitest run`, `npx tsc -b`, `npm run build`, `npx eslint` — all clean.
- [ ] **Step 5: Commit.** `git commit -m "feat(fe): taxonomy pickers + parent select in editor, capability/source facets in marketplace"`

---

## Task 9: Per-key usage attribution (`api_key_id`)

**Files:**
- Modify: `backend/app/models/usage_event.py` (add `api_key_id: UUID | None` FK→`api_keys.id`, indexed, nullable), `backend/app/services/api_key_service.py` (`authenticate` returns `(user_id, api_key_id)`), `backend/app/api/deps.py` (`require_api_key` exposes the key id — extend `CurrentUser` with `api_key_id: UUID | None = None`, set it in the API-key path, `None` in the JWT path), `backend/app/api/v1/routers/sdk.py` (pass `current.api_key_id` into usage writes), `backend/app/services/marketplace_service.py` + `backend/app/repositories/marketplace_repo.py` (`add_usage(..., api_key_id=None)` threaded from `fetch_skill`/`report_usage`).
- Create: migration `backend/migrations/versions/<rev>_usage_events_api_key_id.py`, `backend/tests/integration/test_per_key_usage.py`.

**Interfaces:**
- Consumes: existing `require_api_key`, `add_usage`.
- Produces: `ApiKeyService.authenticate(key) -> tuple[UUID, UUID] | tuple[None, None]`; `CurrentUser.api_key_id`; `add_usage(listing_id, user_id, kind, meta, api_key_id=None)`.

- [ ] **Step 1: Migration** (head check via `alembic heads`; nullable indexed FK column).
- [ ] **Step 2: Failing test** `test_per_key_usage.py` — create a key, call `GET /sdk/skill/{id}` with it, assert the written `usage_events` row has `api_key_id == key.id`; an anonymous/public usage path writes `api_key_id IS NULL`. (Copy key+SDK fixtures from `tests/integration/test_api_keys_sdk.py`.)
- [ ] **Step 3: Run it (RED).**
- [ ] **Step 4: Implement** the signature changes; update ALL existing `authenticate`/`add_usage` callers (grep to be exhaustive) so non-SDK callers pass `None`. Update `test_api_keys_sdk.py` if it asserts the old `authenticate` return shape.
- [ ] **Step 5: Run it (GREEN)** + `test_api_keys_sdk.py` + `test_marketplace_insights.py`.
- [ ] **Step 6: Commit.** `git commit -m "feat(usage): attribute usage_events to api_key_id (SDK calls), NULL for anonymous"`

---

## Task 10: Per-key usage API

**Files:**
- Modify: `backend/app/api/v1/routers/api_keys.py` (add `GET /api-keys/{key_id}/usage`), `backend/app/repositories/api_key_repo.py` (ownership check), `backend/app/repositories/marketplace_repo.py` (aggregate usage by `api_key_id`).
- Test: extend `backend/tests/integration/test_api_keys_sdk.py`.

**Interfaces:**
- Consumes: `api_key_id` on usage events (Task 9), `get_current_user` (JWT).
- Produces: `GET /api-keys/{key_id}/usage` → `{total: int, last_used_at: str | None, by_kind: {kind: count}, by_skill: [{listing_id, title, count}], recent: [{kind, listing_id, created_at}]}`. Key not owned by caller → `404`.

- [ ] **Step 1: Failing test** — owner gets aggregated counts after two SDK calls (total==2, by_kind has fetch); a different user requesting that key_id → 404.
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** the aggregate query + ownership gate.
- [ ] **Step 4: Run it (GREEN).**
- [ ] **Step 5: Commit.** `git commit -m "feat(api-keys): owner-scoped GET /api-keys/{id}/usage aggregation"`

---

## Task 11: Per-key usage panel (frontend)

**Files:**
- Create: `frontend/src/features/settings/components/KeyUsagePanel.tsx`, `frontend/src/features/settings/components/__tests__/KeyUsagePanel.test.tsx`, plus a usage api method in the existing settings/api-keys api module.
- Modify: the API-keys settings page to mount `KeyUsagePanel` per key (expandable row or detail).

**Interfaces:**
- Consumes: `GET /api-keys/{id}/usage` (Task 10).
- Produces: `<KeyUsagePanel keyId={string} />` showing total, last-used (mono), by-kind, recent list — Swiss styling (mono for counts/timestamps, hairline, no shadow).

- [ ] **Step 1: Vitest failing test** — renders total + by_kind from a mocked usage response; shows an empty state when `total===0`.
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** + mount in settings.
- [ ] **Step 4: Run** vitest + tsc + build + eslint clean.
- [ ] **Step 5: Commit.** `git commit -m "feat(fe): per-key usage panel in API-key settings"`

---

## Task 12: SDK download endpoint + build step

**Files:**
- Modify: `backend/app/api/v1/routers/sdk.py` (add `GET /sdk/download`).
- Create: `backend/tests/integration/test_sdk_download.py`; a build target `backend/scripts/build_sdk.py` (or a Makefile target) that runs `uv build` / `python -m build` in `sdk/python/` into `sdk/python/dist/`.

**Interfaces:**
- Consumes: the artifact path under `sdk/python/dist/`.
- Produces: `GET /sdk/download` → `FileResponse` of the newest file in `sdk/python/dist/` with header `X-Checksum-SHA256: <hex>` + `Content-Disposition` attachment; empty/missing `dist/` → `503 {"ok": false, "reason": "SDK artifact not built"}`. **Public** (no auth) — mirror the auth-free pattern from `public.py`.

- [ ] **Step 1: Failing test** `test_sdk_download.py` — with a synthetic file in a temp dist dir (monkeypatch the dist path), `GET /sdk/download` returns 200, `X-Checksum-SHA256` matching the file's sha256, and attachment disposition; empty dist dir → 503 with `{"ok": false}`.
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** endpoint (resolve newest artifact, sha256, FileResponse / 503) + the build script.
- [ ] **Step 4: Run it (GREEN).**
- [ ] **Step 5: Commit.** `git commit -m "feat(sdk): GET /sdk/download serves built artifact + checksum, honest 503 when unbuilt"`

---

## Task 13: SDK docs page + prefilled snippet (frontend)

**Files:**
- Create: `frontend/src/features/sdk/pages/SdkDocsPage.tsx`, `frontend/src/features/sdk/api/sdkApi.ts`, `frontend/src/features/sdk/docs.ts` (the quickstart content as a module), `frontend/src/features/sdk/pages/__tests__/SdkDocsPage.test.tsx`.
- Modify: `frontend/src/app/layouts/nav.ts` + `frontend/src/router/index.tsx` (authed `/sdk` route).

**Interfaces:**
- Consumes: `GET /sdk/download` (Task 12), the existing `MarkdownPreview` component, the marketplace list for the skill-id dropdown.
- Produces: a docs page with install + quickstart + API reference + a **snippet prefilled with a selected skill id** (key read from `EAKSO_API_KEY`, never embedded) + a Download SDK button hitting `/sdk/download`.

- [ ] **Step 1: Vitest failing test** — page renders the quickstart heading, a Download button (link/handler to `/sdk/download`), and a snippet that updates the embedded skill id when a skill is selected, and that the snippet contains `EAKSO_API_KEY` and NOT any literal key.
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** page + content + route + nav entry.
- [ ] **Step 4: Run** vitest + tsc + build + eslint clean.
- [ ] **Step 5: Commit.** `git commit -m "feat(fe): in-app SDK docs page with download + prefilled skill snippet"`

---

## Task 14: "Test your key" playground (frontend)

**Files:**
- Create: `frontend/src/features/sdk/pages/PlaygroundPage.tsx`, `frontend/src/features/sdk/api/playgroundApi.ts`, `frontend/src/features/sdk/pages/__tests__/PlaygroundPage.test.tsx`.
- Modify: `frontend/src/app/layouts/nav.ts` + `frontend/src/router/index.tsx` (authed `/sdk/playground` route).

**Interfaces:**
- Consumes: the user's keys (existing list endpoint), the marketplace list (skill picker), `GET /sdk/skill/{id}` (real SDK endpoint, called with the chosen `sk_live_…` key as Bearer), `GET /api-keys/{id}/usage` (Task 10) to confirm the recorded event.
- Produces: a page where the user picks a key + skill → "Run" → shows the response (`system_prompt`/`content`) on success, the **real 401** body on an invalid/revoked key, and a "usage recorded" confirmation that re-fetches the key's usage and shows the count incremented.

- [ ] **Step 1: Vitest failing test** — on Run with a mocked 200 from `/sdk/skill/{id}`, the response renders and a "usage recorded" indicator appears; on a mocked 401, an error notice renders (no faked success).
- [ ] **Step 2: Run it (RED).**
- [ ] **Step 3: Implement** the playground (real fetch with the key as Bearer; honest error surfacing) + route + nav.
- [ ] **Step 4: Run** vitest + tsc + build + eslint clean.
- [ ] **Step 5: Commit.** `git commit -m "feat(fe): test-your-key playground (real fetch + usage confirmation)"`

---

## Task 15: Deep edge-case test pass + hardening

**Files:**
- Create/extend: backend tests for the gaps below; no production code unless a test reveals a bug (then fix root-cause via systematic-debugging).

**Edge cases to cover (add the missing ones):**
- Concept with BOTH an unknown capability and unknown source in one save → both proposed, save succeeds.
- Reparenting a concept (parent A, then parent B) leaves exactly one `PARENT_OF` edge (clear_parent works).
- Merge a `proposed` capability that two concepts use → both concepts' edges repoint to the target; alias node gone.
- Faceted filter with a capability no listing has → `[]` (not error).
- `add_usage` from the non-SDK marketplace path still works with `api_key_id=NULL`.
- `GET /api-keys/{id}/usage` for a revoked key still returns its historical usage (revocation doesn't delete events).
- `/sdk/download` content-type is an octet-stream/attachment; checksum header present and correct.
- `seed_taxonomy` + `seed_marketplace` run together on boot without collision.

- [ ] **Step 1:** Run the full backend suite; list which edge cases above already have coverage vs. missing.
- [ ] **Step 2:** Add the missing tests (RED where they expose a gap).
- [ ] **Step 3:** Fix any real bugs at root cause; re-run.
- [ ] **Step 4:** Full backend suite green + frontend `tsc -b` + `npm run build` + `npx vitest run` + `npx eslint` all clean.
- [ ] **Step 5: Commit.** `git commit -m "test: deep edge-case coverage for taxonomy, hierarchy, facets, per-key usage, SDK download"`

---

## Definition of Done
- Capabilities & sources are graph-native terms with a seeded canonical hierarchy; unknown terms become `proposed` (never rejected) and are curatable (promote/merge) by admins.
- Concepts carry `sources` and support `PARENT_OF` sub-concept nesting with cycle prevention.
- Marketplace browse is faceted by capability/source.
- `usage_events` are attributed to `api_key_id`; owners see per-key usage; the SDK is downloadable with in-app docs + a prefilled snippet; the playground exercises a real key end-to-end.
- Full backend suite green; frontend `tsc -b` + `build` + `vitest` + `eslint` clean; edge cases covered.
