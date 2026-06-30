# Phase 1 — "Make it work & trust it"

Status: approved 2026-06-29. Scope: embedding reliability + reindex, and interactive
(grade-vs-expected) evaluation. Part of a larger 3-phase effort (Phase 2: graph
overview UX + versioning; Phase 3: marketplace + usage SDK + insight dashboards).

## Root causes addressed (verified against live data)

- **Embeddings "0000000":** `OpenRouterProvider.embed()` swallows every error
  (incl. constant 429s) and silently substitutes a sparse `local_embedding` hash
  vector, which is then persisted permanently with no retry and no reindex path.
  OpenRouter embeddings actually work (verified dense 1536-dim output). The stored
  `lineage.md` vector has 5/1536 non-zero values — the hash-fallback signature.
- **Empty graph:** not a backend bug — exactly 1 concept file exists on disk. The
  UX is search-gated and has no overview. (Overview UX is Phase 2.)

## Part A — Embedding reliability & reindex

1. Concept nodes gain `embedding_status`: `ok | pending | failed`.
2. Indexing distinguishes a *real* embedding from the hash fallback (provider
   surfaces an `is_real` flag). Real → store vector + `status=ok`. Not real /
   failed → `status=pending`, **no fake vector stored**.
3. Semantic search ranks only `embedding_status='ok'` nodes.
4. Healing:
   - Immediate: after create/update returns, a FastAPI `BackgroundTask` retries
     the embed for that node if pending (no Celery — stubbed in repo).
   - Manual: `POST /workspaces/{id}/reindex` re-embeds all / pending; surfaced as a
     "Reindex workspace" button on the Knowledge Graph page. Backfills the bad node.
5. Reindex clears stale `REFERENCES` edges before recreating them.

## Part B — Interactive evaluation (grade vs expected)

1. Test case = `{input, expected}`. Persisted as a git-versioned bundle file next
   to the skill: `<dir>/<slug>.eval.yaml` (`{cases: [{input, expected}]}`).
2. `GradeEvaluator`: per case → run skill on `input` (answer-with-skill) → actual →
   judge `actual vs expected` → `{score 0-10, passed, reasoning}`. Aggregates
   pass-rate + avg score. Reuses the Pydantic AI `EvalAgent` (structured + retries).
3. Suggest-cases: LLM drafts `{input, expected}` rows from the skill body; leaves
   `expected` blank when it cannot infer it.
4. Endpoints (under the concepts router):
   - `GET  /workspaces/{id}/concept/eval-cases?path=` → load saved cases
   - `PUT  /workspaces/{id}/concept/eval-cases?path=` → save (commits the file)
   - `POST /workspaces/{id}/concept/suggest-eval-cases?path=&n=` → LLM drafts
   - `POST /workspaces/{id}/concept/grade-eval?path=` (body: cases) → run grading
5. Frontend: a "Test cases" tab in the concept editor — editable `input | expected`
   table, *Suggest cases*, *+ add row*, *Run N scenarios*; results add
   `actual | score | pass/fail | reasoning` columns plus an aggregate header.

## Cross-cutting

- Saves never blocked by embedding or eval failures.
- Tests: GradeEvaluator (fake agent), embedding real-vs-fallback + status +
  search-exclusion + reindex heal, suggest-cases blanks; frontend type-check.
