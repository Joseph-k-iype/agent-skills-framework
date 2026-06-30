# Phase 2 — "See & version"

Status: approved 2026-06-29. Scope: rich knowledge-graph overview UX + document
version control (diff / restore / preview) with published versions tracked in the
graph. Builds on Phase 1 (reindex/heal). Phase 3 (marketplace + usage SDK +
insight dashboards) remains queued.

## Part A — Knowledge Graph overview (rich explorer)

- Backend: `GET /workspaces/{id}/graph` is enriched — each node also carries
  `description`, `runtime`, and a `versions` count (via `HAS_VERSION`). Hub sizing
  (degree) is computed client-side from edges.
- Frontend: new `GraphExplorer` (React Flow + `@dagrejs/dagre` auto-layout). Node
  size ∝ connectivity, color by `type`; click → highlight neighborhood + details
  panel (Open → editor); type-filter chips; search-to-focus. `KnowledgeGraphPage`
  is restructured so the canvas is the primary view; semantic search feeds it.

## Part B — Versioning (manage + track in graph)

- `BundleRepo` git ops: `read_file_at(path, ref)` (`git show`), `diff(path, a, b)`
  (unified), `restore(path, ref, msg, author)` (writes old content as a NEW commit
  — non-destructive), `list_tags()` (parses each publish tag's
  `publish <path> v<version>` subject into `{tag, path, version, ts}`).
- Versions in the graph: on publish, besides the git tag, create
  `(Concept)-[:HAS_VERSION]->(Version{key, tag, version, ts})`. `reindex_workspace`
  rebuilds these from git tags so they survive a projection rebuild.
- Endpoints (concepts router): `GET /concept/version?path=&ref=`,
  `GET /concept/diff?path=&a=&b=`, `POST /concept/restore?path=&ref=`,
  `GET /concept/versions?path=`. Existing `/concept/history` stays.
- Frontend: History tab becomes a version manager — commit history + published
  version lineage; per entry Preview (read-only), Restore, and Diff (pick two →
  unified diff viewer).

## Cross-cutting

- Restore re-indexes + heals embeddings (Phase 1). Publish never corrupts git.
- Tests: BundleRepo read-at/diff/restore/list_tags; version-node create +
  reindex rebuild; graph node enrichment; frontend tsc/eslint/build.
