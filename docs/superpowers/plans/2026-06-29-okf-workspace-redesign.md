# OKF Workspace Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a workspace a real git-backed directory of OKF markdown files (skills/agents/concepts) with body+mermaid editing, free-text runtime, a FalkorDB index projected from the files, semantic search, and 6 hybrid eval agents.

**Architecture:** Files on disk are the source of truth (one git repo per workspace under `WORKSPACES_ROOT`). A parser turns each `.md` concept (YAML frontmatter + body, markdown links = edges) into FalkorDB nodes/edges — a *projection*, never authored directly. A pluggable `LLMProvider` backs embeddings and the 6 evaluators; with no key, everything degrades to deterministic/offline behavior. Frontend gets a file-tree workspace and a split markdown/mermaid concept editor.

**Tech Stack:** Python/FastAPI, GitPython (or subprocess git), FalkorDB, PostgreSQL (auth/RBAC only), Pydantic, pytest; React 19 + Vite + AntD + TanStack Query, `react-markdown` + `remark-gfm` + `mermaid`.

## Global Constraints

- Source of truth = real files on disk; FalkorDB is a rebuilt projection, never authored directly.
- `WORKSPACES_ROOT` is configurable via env; never hardcode a path.
- `runtime` and `type` are free text — no enums, no dropdowns restricting values.
- LLM provider is pluggable via `settings.llm_provider`; no key ⇒ deterministic offline fallback (hash embeddings, rules-only evals). Never hardcode OpenRouter.
- OKF permissiveness: never reject a bundle for unknown `type`, unknown keys, missing optional fields, or broken links.
- Reserved filenames `index.md` / `log.md` are not concepts.
- Out of scope this round (do not touch beyond keeping them compiling): marketplace, workflow execution, analytics, community.
- TDD: failing test first; commit per task. Tests run via `uv run --python 3.12 ...` (system python is 3.9).

---

## File Structure

**Backend — new:**
- `app/storage/repo.py` — git-backed bundle filesystem ops (read/write/move/delete files & dirs, commit, tag, log).
- `app/storage/paths.py` — `WORKSPACES_ROOT` resolution, slug/path helpers, path-safety guard.
- `app/llm/provider.py` — `LLMProvider` protocol + registry + `get_provider()`.
- `app/llm/providers/local.py` — offline provider (hash embeddings, no chat).
- `app/llm/providers/openrouter.py` — OpenRouter provider (chat + embed).
- `app/llm/providers/anthropic.py`, `openai_provider.py` — optional chat/embed via config.
- `app/okf/concept.py` — `Concept` model (frontmatter + body + computed links).
- `app/services/concept_service.py` — create/read/update/move/delete concept files + commit + reindex.
- `app/services/index_service.py` — parse bundle → upsert FalkorDB nodes/edges + embeddings.
- `app/evals/base.py` — `Evaluator` ABC (`run_rules`, optional `run_llm_judge`), `EvalFinding`, `EvalResult`.
- `app/evals/security.py`, `documentation.py`, `governance.py`, `cost.py`, `performance.py`, `quality.py`.
- `app/evals/supervisor.py` — runs all six, aggregates.
- `app/api/v1/routers/concepts.py` — concept file CRUD + eval endpoints.

**Backend — modified:**
- `app/core/config.py` — add `workspaces_root`, `llm_provider`, provider keys.
- `app/services/workspace_service.py` — workspace = git repo; folders = directories.
- `app/repositories/workspace_graph_repo.py` / `okf_graph_repo.py` — projection upserts keyed by file path.
- `app/services/okf_service.py` — repurpose discover/ingest to operate on a workspace repo (the bundle), not an external path.
- `app/api/v1/routers/skills.py` — fold into concepts (skill = concept with `type: skill`).

**Frontend — new/modified:**
- `features/workspace/pages/WorkspacePage.tsx` — file-tree CRUD + drag/drop.
- `features/concepts/pages/ConceptEditorPage.tsx` — replaces `skills/pages/SkillEditorPage.tsx`; split frontmatter form + markdown/mermaid editor.
- `features/concepts/components/MarkdownPreview.tsx` — `react-markdown` + mermaid.
- `features/concepts/components/EvaluatorPanel.tsx` — run + show 6 evals.
- `features/concepts/api/conceptApi.ts` — file + eval endpoints.

---

## Phase 1 — Foundation: config, git-backed storage, provider abstraction

### Task 1: Settings for root path + provider

**Files:** Modify `backend/app/core/config.py`; Test `backend/tests/unit/test_config_redesign.py`

**Interfaces — Produces:** `settings.workspaces_root: str`, `settings.llm_provider: str` (default `"local"`), `settings.anthropic_api_key`, `settings.openai_api_key` (default `""`).

- [ ] **Step 1:** Write failing test asserting `settings.workspaces_root` defaults to a path ending in `workspaces` and `settings.llm_provider == "local"` when no env set.
- [ ] **Step 2:** Run: `uv run --python 3.12 --with pytest --with pydantic-settings pytest backend/tests/unit/test_config_redesign.py -v` → FAIL.
- [ ] **Step 3:** Add fields to `Settings`: `workspaces_root: str = str(Path(__file__).resolve().parents[3] / "data" / "workspaces")`, `llm_provider: str = "local"`, `anthropic_api_key: str = ""`, `openai_api_key: str = ""`.
- [ ] **Step 4:** Run test → PASS.
- [ ] **Step 5:** Commit `feat(config): add workspaces_root + pluggable llm_provider settings`.

### Task 2: Path helpers + safety guard

**Files:** Create `backend/app/storage/paths.py`; Test `backend/tests/unit/test_storage_paths.py`

**Interfaces — Produces:**
- `workspace_root(workspace_id: str) -> Path`
- `safe_join(root: Path, *parts: str) -> Path` (raises `ValueError` on traversal outside root)
- `slugify(name: str) -> str`

- [ ] **Step 1:** Failing tests: `safe_join(root, "a/b.md")` stays under root; `safe_join(root, "../escape")` raises `ValueError`; `slugify("My Skill!") == "my-skill"`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement with `Path.resolve()` containment check (`resolved.is_relative_to(root)`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(storage): path helpers + traversal guard`.

### Task 3: Git-backed bundle repo

**Files:** Create `backend/app/storage/repo.py`; Test `backend/tests/unit/test_storage_repo.py`

**Interfaces — Produces:** class `BundleRepo`:
- `BundleRepo.init(workspace_id) -> BundleRepo` (git init if absent, initial commit)
- `write_file(rel_path: str, content: str, message: str, author: str) -> str` (returns commit sha)
- `read_file(rel_path: str) -> str`
- `delete_path(rel_path: str, message: str, author: str) -> str`
- `move_path(src: str, dst: str, message: str, author: str) -> str`
- `make_dir(rel_path: str) -> None` (writes `.gitkeep`)
- `list_files() -> list[str]` (all `.md`, repo-relative, sorted)
- `history(rel_path: str | None = None) -> list[dict]` (sha, message, author, ts)
- `tag(name: str, message: str) -> None`

Use `subprocess` git (no new dep) via a helper; isolate so tests use a tmp `WORKSPACES_ROOT` (monkeypatch `settings.workspaces_root`).

- [ ] **Step 1:** Failing test: init repo in tmp dir, `write_file("a/x.md","# hi","add x","admin")` returns sha; `read_file` round-trips; `list_files() == ["a/x.md"]`; `history()` has 1+ entries; `move_path` then `read_file(dst)` works; `delete_path` removes it.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `BundleRepo` using `subprocess.run(["git", ...], cwd=repo_dir, check=True)`, env with `GIT_AUTHOR_*`/committer set, `core` user fallback configured at init.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(storage): git-backed bundle repo (write/read/move/delete/history/tag)`.

### Task 4: LLMProvider abstraction + local + openrouter

**Files:** Create `app/llm/provider.py`, `app/llm/providers/local.py`, `app/llm/providers/openrouter.py`, `app/llm/providers/anthropic.py`, `app/llm/providers/openai_provider.py`; move existing hash logic from `app/llm/openrouter.py`; Test `backend/tests/unit/test_llm_provider.py`

**Interfaces — Produces:**
```python
class LLMProvider(Protocol):
    name: str
    @property
    def has_chat(self) -> bool: ...
    @property
    def using_real_embeddings(self) -> bool: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def chat(self, system: str, user: str) -> str | None: ...  # None if no chat
def get_provider() -> LLMProvider  # selected by settings.llm_provider
```
`local`: hash embeddings (reuse `local_embedding`), `chat` returns `None`, `has_chat=False`. `openrouter`/`anthropic`/`openai`: real embed+chat when key present, else fall back to local embeddings and `chat=None`.

- [ ] **Step 1:** Failing tests: `get_provider()` with `llm_provider="local"` → `embed` returns vectors of `settings.embedding_dim`, `await chat(...) is None`, `has_chat is False`. With `llm_provider="openrouter"` and no key → still embeds via local fallback.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement protocol + registry `{"local":..,"openrouter":..,"anthropic":..,"openai":..}`; keep `get_llm()` in `openrouter.py` as a thin `get_provider()` alias for back-compat, update imports in `okf_service.py`.
- [ ] **Step 4:** Run → PASS; also run existing `test_*` that import `get_llm`.
- [ ] **Step 5:** Commit `feat(llm): pluggable provider abstraction (local/openrouter/anthropic/openai)`.

---

## Phase 2 — Concept model, file CRUD, graph projection, search

### Task 5: Concept model (frontmatter + body + computed links)

**Files:** Create `app/okf/concept.py`; extend `app/okf/parser.py`; Test `backend/tests/unit/test_concept_model.py`

**Interfaces — Produces:**
```python
@dataclass
class Concept:
    path: str            # repo-relative, e.g. "finance/payments/invoice-ocr.md"
    type: str            # required frontmatter
    title: str
    description: str | None
    runtime: str | None  # free text
    tags: list[str]
    capabilities: list[str]
    frontmatter: dict    # full raw frontmatter (unknown keys preserved)
    body: str
    links: list[str]     # resolved repo-relative targets of markdown links
def parse_concept(rel_path: str, content: str) -> Concept
def to_markdown(concept_fields: dict, body: str) -> str  # frontmatter + body serializer
```
`parse_concept` must default `type` to `"document"` if absent (permissive), preserve unknown frontmatter keys, and resolve relative links against the file's directory to repo-relative paths.

- [ ] **Step 1:** Failing tests: parse a doc with `type: skill`, `runtime: python 3.12`, body link `[v](../x.md)` → `links == ["dir/x.md"]` resolved; unknown key `owner: jo` preserved in `.frontmatter`; missing `type` → `"document"`. `to_markdown({...}, "# b")` round-trips through `parse_concept`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement using existing `frontmatter` lib + link resolution via `PurePosixPath`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(okf): Concept model with free-text type/runtime + resolved links`.

### Task 6: Index service (bundle → FalkorDB projection)

**Files:** Create `app/services/index_service.py`; adjust `app/repositories/okf_graph_repo.py` to key nodes by `(workspace_id, path)`; Test `backend/tests/integration/test_index_projection.py` (skips if FalkorDB unavailable)

**Interfaces — Produces:**
```python
class IndexService:
    async def reindex_workspace(self, workspace_id: str) -> IngestionResult
    async def index_concept(self, workspace_id: str, path: str) -> None
    def remove_concept(self, workspace_id: str, path: str) -> None
```
Upserts `Concept` nodes (label by capitalized `type` plus generic `:Concept`), `CONTAINS` edges to folders by path, `REFERENCES` edges from resolved links, embeddings from `provider.embed`. Reindex clears the workspace's projected nodes first (idempotent).

- [ ] **Step 1:** Failing test (guarded by FalkorDB ping): write 2 linked concepts to a tmp BundleRepo, `reindex_workspace` → graph has 2 `:Concept` nodes + 1 `REFERENCES` edge; `remove_concept` drops one.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement; reuse content-hash embed-dedup pattern from `okf_service.py`.
- [ ] **Step 4:** Run → PASS (or SKIP cleanly without FalkorDB).
- [ ] **Step 5:** Commit `feat(index): project workspace bundle into FalkorDB (idempotent reindex)`.

### Task 7: Concept service (file CRUD + commit + reindex)

**Files:** Create `app/services/concept_service.py`; Test `backend/tests/integration/test_concept_service.py`

**Interfaces — Produces:**
```python
class ConceptService:
    def __init__(self, db, user)
    async def create(self, workspace_id, folder_path, name, type, frontmatter, body) -> ConceptOut
    async def get(self, workspace_id, path) -> ConceptOut
    async def update(self, workspace_id, path, frontmatter, body) -> ConceptOut
    async def move(self, workspace_id, src_path, dst_folder_path) -> ConceptOut
    async def delete(self, workspace_id, path) -> None
    def history(self, workspace_id, path) -> list[VersionEntry]
    async def publish(self, workspace_id, path, version) -> ConceptOut  # git tag
```
Each mutation: write/move/delete via `BundleRepo`, then `IndexService.index_concept`/`remove_concept`, then audit. `ConceptOut` includes computed `links`/`references` (read-only) and `runtime` free text.

- [ ] **Step 1:** Failing test: `create(...)` writes a file & node; `update` changes body & commit count grows; `history` returns ≥2 entries; `move` relocates file; `delete` removes file + node.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement; reuse `WorkspaceService` audit pattern.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(concepts): file-backed concept CRUD with git history + reindex`.

### Task 8: Workspace = git repo; folders = directories

**Files:** Modify `app/services/workspace_service.py`, `app/repositories/workspace_graph_repo.py`; Test update `backend/tests/integration/test_workspace_service.py`

**Interfaces — Consumes:** `BundleRepo`, `IndexService`. **Produces:** workspace create → `BundleRepo.init`; folder create/rename/move/delete → directory ops + reindex; graph stays a projection.

- [ ] **Step 1:** Failing test: create workspace → repo dir exists with initial commit; create folder → directory exists; move folder → dir moved + paths recomputed; delete → gone.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: keep existing graph methods but drive them from filesystem truth; add repo ops.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(workspace): back workspaces/folders with git repo + directories`.

### Task 9: Concepts router + fold skills in; semantic search

**Files:** Create `app/api/v1/routers/concepts.py`; modify `app/api/v1/router.py`, `app/api/v1/routers/skills.py` (compat: skill = concept `type=skill`), `app/services/knowledge_service.py` (search over projection); Test `backend/tests/integration/test_concepts_api.py`

**Interfaces — Produces (REST):** `POST/GET/PUT/DELETE /workspaces/{id}/concepts`, `POST /concepts/{...}/move`, `GET /concepts/{...}/history`, `POST /concepts/{...}/publish`, `POST /concepts/{...}/evaluate`, `GET /workspaces/{id}/search?q=`.

- [ ] **Step 1:** Failing API test (TestClient): create workspace → create concept → GET returns body+frontmatter → search returns it.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement router wired to `ConceptService` + RBAC deps; keep `/skills` endpoints returning concepts with `type=skill` for back-compat.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(api): concept file endpoints + search over projection`.

---

## Phase 3 — Eval agents (hybrid rules + pluggable LLM)

### Task 10: Evaluator base + result types

**Files:** Create `app/evals/base.py`; Test `backend/tests/unit/test_evals_base.py`

**Interfaces — Produces:**
```python
@dataclass
class EvalFinding: severity: str; message: str; evidence: str | None
@dataclass
class EvalResult: evaluator: str; score: float; findings: list[EvalFinding]; blocking: bool; used_llm: bool
class Evaluator(ABC):
    name: str
    def run_rules(self, concept: Concept) -> EvalResult: ...
    async def run_llm_judge(self, concept: Concept, provider: LLMProvider) -> EvalResult | None: ...
    async def evaluate(self, concept: Concept, provider: LLMProvider) -> EvalResult  # merges rules + optional llm
```
`evaluate` always runs rules; calls `run_llm_judge` only if `provider.has_chat`; merges findings and combines scores.

- [ ] **Step 1:** Failing test: a dummy evaluator with rules-only returns `used_llm=False` under local provider.
- [ ] **Step 2–4:** Implement + pass.
- [ ] **Step 5:** Commit `feat(evals): evaluator base + result types`.

### Task 11: Six evaluators

**Files:** Create `app/evals/{security,documentation,governance,cost,performance,quality}.py`; Test `backend/tests/unit/test_evaluators.py`

**Interfaces — Produces:** one `Evaluator` subclass each. Rule behavior:
- **Security:** regex secret scan (API keys, `AKIA`, private keys, `password=`), unsafe-prompt phrases → blocking on match.
- **Documentation:** broken relative links (target not in bundle list), malformed mermaid fences, missing `title`/`description`.
- **Governance:** missing required frontmatter (`type`), non-kebab filename, missing owner/tags policy.
- **Cost:** estimate tokens (`len(body)//4`) → score band.
- **Performance:** body length / nesting heuristics.
- **Quality:** rules (has sections, has examples) + optional LLM judge prompt for correctness/completeness.

- [ ] **Step 1:** Failing tests, one per evaluator, asserting a known-bad concept produces a finding and a clean one scores high. (e.g. body with `AWS_SECRET_ACCESS_KEY=AKIA...` → Security blocking.)
- [ ] **Step 2–4:** Implement each + pass. `bundle_files` passed in for link checks.
- [ ] **Step 5:** Commit `feat(evals): six evaluators (security/docs/governance/cost/perf/quality)`.

### Task 12: Eval supervisor + wire endpoint

**Files:** Create `app/evals/supervisor.py`; wire `POST /concepts/{...}/evaluate`; Test `backend/tests/integration/test_eval_supervisor.py`

**Interfaces — Produces:**
```python
class EvalSupervisor:
    async def evaluate(self, concept: Concept, bundle_files: list[str]) -> EvalReport
@dataclass
class EvalReport: overall_score: float; confidence: float; results: list[EvalResult]; blocking_issues: list[str]; recommendations: list[str]
```
Runs all six concurrently (`asyncio.gather`), aggregates weighted score, collects blocking issues.

- [ ] **Step 1:** Failing test: clean concept → no blocking; secret-laden concept → `blocking_issues` non-empty, lower score. Works under local provider (rules-only).
- [ ] **Step 2–4:** Implement + pass.
- [ ] **Step 5:** Commit `feat(evals): supervisor aggregation + /evaluate endpoint`.

---

## Phase 4 — Frontend: workspace tree + concept editor + evaluator panel

### Task 13: Concept API client + mermaid markdown preview

**Files:** Add deps `react-markdown`, `remark-gfm`, `mermaid`; create `features/concepts/api/conceptApi.ts`, `features/concepts/components/MarkdownPreview.tsx`; Test `frontend/src/features/concepts/__tests__/MarkdownPreview.test.tsx`

**Interfaces — Produces:** `useConcept(ws,path)`, `useUpdateConcept`, `useCreateConcept`, `useEvaluateConcept`, `useConceptHistory`; `<MarkdownPreview source={md} />` renders markdown and executes ```mermaid``` fences via `mermaid.render`.

- [ ] **Step 1:** Failing test: `MarkdownPreview` with a `# Heading` renders an `<h1>`; with a mermaid fence calls `mermaid.render` (mock).
- [ ] **Step 2–4:** `npm i react-markdown remark-gfm mermaid`; implement; pass `npm test`.
- [ ] **Step 5:** Commit `feat(fe): concept api client + mermaid markdown preview`.

### Task 14: Concept editor page (replaces SkillEditor)

**Files:** Create `features/concepts/pages/ConceptEditorPage.tsx`; modify `router/*` to route `/concepts/:workspaceId/*path`; delete `features/skills/pages/SkillEditorPage.tsx` (and its OKF-References tab); Test `frontend/src/features/concepts/__tests__/ConceptEditor.test.tsx`

**Interfaces — Consumes:** conceptApi. Layout: left frontmatter form — **runtime = `AutoComplete` free text** (suggestions but free entry), `type` free text, tags, capabilities; right — markdown body `textarea`/CodeMirror + live `<MarkdownPreview>`. Read-only "Linked concepts" panel from `concept.links`. No "OKF References" tab.

- [ ] **Step 1:** Failing test: editing the runtime field accepts arbitrary text "rust 1.79"; typing body updates preview; there is no element with text "OKF References".
- [ ] **Step 2–4:** Implement; pass.
- [ ] **Step 5:** Commit `feat(fe): concept editor with markdown/mermaid + free-text runtime`.

### Task 15: Workspace file-tree + evaluator panel

**Files:** Modify `features/workspace/pages/WorkspacePage.tsx`, `features/workspace/components/buildTree.ts`; create `features/concepts/components/EvaluatorPanel.tsx`; Tests update `buildTree.test.ts`, add `EvaluatorPanel.test.tsx`

**Interfaces — Produces:** tree shows folders+files from the bundle; create/rename/move/delete via API; clicking a file opens `ConceptEditorPage`. `<EvaluatorPanel concept />` runs `/evaluate` and shows 6 results + aggregate + blocking issues.

- [ ] **Step 1:** Failing tests: `buildTree` nests folder/file rows from a flat path list; EvaluatorPanel renders 6 evaluator rows from a mocked report.
- [ ] **Step 2–4:** Implement; pass.
- [ ] **Step 5:** Commit `feat(fe): workspace file-tree + evaluator panel`.

---

## Phase 5 — Complete & verify

### Task 16: Remove dead split-model code

**Files:** Delete/disable `references`-as-editable in `schemas/skill.py`; remove separate `OKFDocument` ingestion-from-external-path UI; ensure `skills` endpoints alias concepts; grep for `OKF References`, hardcoded `python`/`typescript`, direct `OpenRouterClient()` construction.

- [ ] **Step 1:** `grep -rn "OKF References\|value: \"python\"\|value: \"typescript\"" frontend/src` → empty.
- [ ] **Step 2:** `grep -rn "import.*openrouter import get_llm" backend/app` → only via provider shim.
- [ ] **Step 3:** Commit `refactor: remove split-model + hardcoded runtime/provider remnants`.

### Task 17: End-to-end green

- [ ] **Step 1:** Backend: `uv run --python 3.12 --with '.[test]' pytest backend/tests -q` → all pass/skip.
- [ ] **Step 2:** Frontend: `cd frontend && npm run lint && npm test && npm run build` → pass.
- [ ] **Step 3:** Manual smoke: start services, create workspace → folder → concept with mermaid → save → search → evaluate. Document result.
- [ ] **Step 4:** Commit `test: end-to-end green for OKF workspace redesign`.

---

## Self-Review notes

- Spec §Storage&git → Tasks 1–3, 7, 8. §Concept model → Tasks 5, 7. §Backend provider → Task 4. §Indexer → Task 6. §Evals → Tasks 10–12. §Frontend → Tasks 13–15. §Removed/changed → Task 16. §Success criteria → Task 17.
- Free-text runtime enforced in Tasks 5 (model), 14 (UI). Pluggable provider in Task 4, consumed in 6/11/12. Git-as-versioning in Tasks 3, 7. No separate OKFDocument in Tasks 9, 16.
