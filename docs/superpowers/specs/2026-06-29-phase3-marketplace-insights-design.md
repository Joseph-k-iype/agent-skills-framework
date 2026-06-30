# Phase 3 — "Marketplace & insights" (SDK deferred)

Status: approved 2026-06-29. Slices: (0) persist eval runs, (3a) marketplace
publish+install, (3b) insight dashboards. The usage-tracking SDK is deferred to a
later slice once usage semantics are settled.

## Slice 0 — Persist eval runs (foundation for insights)

- New Postgres table `eval_runs`: id, workspace_id, concept_path, kind
  (`fast`|`deep`|`grade`), score (float — overall / effectiveness / pass_rate),
  passed (bool|null), summary, payload (JSONB), actor_id, created_at.
- `ConceptService.evaluate / deep_evaluate / grade_eval` persist a row after each
  run (best-effort; never blocks the response).

## Slice 3a — Marketplace (publish + install/copy)

- Rework `MarketplaceListing` to key on the Concept: `source_workspace_id`,
  `source_path`, `title`, `summary`, `type`, `runtime`, `author_id`, `version`,
  `tags`, `is_public` (default true in-deployment), `downloads`, timestamps.
- On publish, upsert a listing for that concept+version.
- Endpoints: `GET /marketplace` (catalog, filter by type/tag/text),
  `GET /marketplace/{id}` (metadata + preview of the published content at its tag),
  `POST /marketplace/{id}/install` ({target_workspace_id, folder_path?}) → copies
  the published markdown + eval cases into the target workspace as a new concept,
  stamps provenance frontmatter (`installed_from`, `source`), indexes it,
  increments `downloads`, audits `CONCEPT_INSTALLED`.
- Frontend: Marketplace catalog page (search + type filter, author/version/downloads),
  listing detail (preview + Install → pick target workspace/folder), nav entry.

## Slice 3b — Insight dashboards

- Analytics endpoint(s) aggregating: eval effectiveness trend + grade pass-rate
  per skill + run counts (from `eval_runs`); most-installed + recent publishes
  (listings/audit); graph analytics — node count by type, version distribution,
  hubs (top by degree), orphans (no edges) — from FalkorDB.
- `GET /analytics/overview?workspace_id=` returns the metric bundle (workspace +
  global).
- Frontend: Insights page — stat cards + a couple of charts (add `recharts`) +
  tables for hubs/most-used.

## Cross-cutting

- Persistence best-effort; failures never break eval/publish/install responses.
- Tests: eval_runs persistence, listing upsert-on-publish, install copies bundle +
  eval cases + provenance + downloads, analytics aggregation; frontend tsc/eslint/build.
