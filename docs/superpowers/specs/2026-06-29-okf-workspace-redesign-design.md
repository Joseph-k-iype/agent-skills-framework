# OKF Workspace Redesign — Design Spec

**Date:** 2026-06-29
**Branch:** feat/eakso-phase-0-3
**Status:** Approved, ready for implementation

---

## Problem

The current implementation modeled a "skill" as a **database record with fixed
form fields and no body**. It invented an artificial split between `Skill`,
`Agent`, `Prompt` and a separate `OKFDocument` entity, plus an "OKF References"
field and an "import OKF into the graph" step. None of this matches what OKF
actually is, nor the user's mental model.

### What OKF actually is

[OKF — Open Knowledge Format v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(Google Cloud, 2026-06-12) is intentionally tiny:

- An OKF **bundle** is just a **directory of markdown files**.
- Each file is a **concept**: YAML frontmatter (only `type` is required) + a
  markdown body.
- Files link to each other with **ordinary markdown links**; those links **are**
  the knowledge graph (untyped directed edges; consumers tolerate broken links).
- Reserved filenames: `index.md` (directory listing, no frontmatter) and
  `log.md` (chronological history). Everything else is a concept.
- Consumers must be permissive: never reject for unknown `type`, unknown keys,
  missing optional fields, or broken links.

The user's description — "a workspace → folders/subfolders → markdown files that
can be agent or sub-agent skills, each with a body where you can draw mermaid
diagrams" — **is already OKF.** The redesign collapses the artificial split.

---

## Approved cornerstone decisions

1. **Source of truth = real git-backed files on disk.** Each workspace is a real
   directory of `.md` files, version-controlled with git. FalkorDB is a *rebuilt
   index/projection*, never authored directly.
2. **Runtime = free-text field.** Today it is a hardcoded `python`/`typescript`
   dropdown; it becomes a field where the user types anything.
3. **Scope this round = the core authoring loop.** Workspace file tree + folders
   + markdown concept files (body editor + mermaid) + free-text runtime + graph
   projection + semantic search + all 6 eval agents. **Deferred:** marketplace,
   workflow execution, analytics, community.
4. **Eval agents = hybrid.** Each evaluator runs deterministic rules always, and
   optionally augments with an LLM via a **pluggable provider**; no key → rules
   only (always produces a score, works offline). Same offline-first pattern as
   the existing embeddings.

---

## Target architecture

```
Workspace (git repo)  ──parse──►  FalkorDB index (nodes + edges)  ──►  search / graph UI
   .md files = concepts                (rebuilt from files,             (projection only)
   links = edges                        never authored directly)
```

### Storage & git

- Configurable data root via `WORKSPACES_ROOT` env (**not hardcoded**).
- **One git repo per workspace** → isolation, free history, export = clone/tarball.
- Folders/subfolders = real directories; files = `<slug>.md`. Reserved
  `index.md` / `log.md` honored.
- **Save = write file + `git commit`. Publish = `git tag`.** This replaces the
  bespoke "version node" system entirely. Version history = `git log`.
- **Postgres** keeps only: users, RBAC, audit, and a thin
  `workspace(id → repo path, permissions)` table.
- **FalkorDB** is purely the rebuilt index.
- RBAC: workspace/folder-level now; per-file later.

### Concept file model

```markdown
---
type: skill            # required. skill | agent | prompt | doc | <anything>
title: Invoice OCR
description: Extracts line items from invoices
runtime: python 3.12   # FREE TEXT — no dropdown
tags: [finance, ocr]
capabilities: [extraction:invoice]
---

# Body — full markdown, renders mermaid

\```mermaid
flowchart LR
  A[Invoice] --> B[OCR] --> C[Line items]
\```

Links to [the validator](../payments/validator.md) become graph edges.
```

- `references` becomes **computed/read-only**, derived from parsed body links —
  never an editable field.
- `type` is free-text; `skill` and `agent` are just conventional values.

### Backend

- **`app/llm/provider.py`** — pluggable `LLMProvider` interface (`chat()` +
  `embed()`). Providers: Anthropic / OpenAI / OpenRouter / local-fallback,
  selected by `settings.llm_provider`. OpenRouter becomes *one* provider, not the
  hardcoded gateway. No key → local fallback (hash embeddings, rules-only evals).
- **Indexer service** — on save: parse file → upsert node + edges in FalkorDB →
  embed body. Full `reindex(workspace)` walks the bundle.
- **Eval supervisor + 6 evaluators** — each = `run_rules()` (always) + optional
  `run_llm_judge(provider)`:
  - **Security** — secret scan, unsafe-prompt heuristics
  - **Documentation** — broken-link / mermaid-syntax / metadata completeness
  - **Governance** — naming conventions, required frontmatter, structure
  - **Cost** — token estimate
  - **Performance** — complexity heuristics (+ optional LLM)
  - **Quality** — correctness/completeness (rules + optional LLM judgment)
  - **Supervisor** aggregates → overall score, confidence, evidence,
    recommendations, blocking issues.
  - Plain async supervisor (deterministic/testable), **not** LangGraph.

### Frontend

- **Workspace page** — real file-tree (folders/subfolders/files): create,
  rename, move, delete, drag-drop → file APIs.
- **Concept editor** (replaces SkillEditor) — left: frontmatter form (runtime =
  free-text AutoComplete, type free-text, tags, capabilities); right: markdown
  body editor + live preview rendering markdown + mermaid (`react-markdown` +
  `remark-gfm` + `mermaid`). "OKF References" tab **deleted**, replaced by a
  read-only "Linked concepts" panel from the graph.
- **Evaluator panel** — run evals → 6 results + aggregate + blocking issues.

---

## Removed / changed

- ❌ "OKF References" tab & `references` as an editable field
- ❌ Separate `OKFDocument` entity distinct from skills/agents
- ❌ Hardcoded `python`/`typescript` runtime dropdown
- ❌ Bespoke version-node system → replaced by git
- ❌ Hardcoded OpenRouter gateway → pluggable provider
- ⚠️ Deferred (untouched this round): marketplace, workflow execution,
  analytics, community

---

## Implementation phases (this round)

1. **Foundation** — `WORKSPACES_ROOT`, git-backed workspace storage, pluggable
   LLM provider abstraction.
2. **Concept model** — frontmatter+body file model, extended parser, indexer,
   FalkorDB graph projection, semantic search over the projection.
3. **Evals** — supervisor + 6 evaluators (rules + optional LLM, offline-safe).
4. **Frontend** — workspace tree, concept editor (markdown + mermaid, free-text
   runtime), evaluator panel; delete OKF-References tab.
5. **Complete & verify** — audit existing code, remove dead split-model code,
   all tests green end-to-end.

---

## Success criteria

- A user can create a workspace, nest folders/subfolders, create `.md` concept
  files, edit a body with mermaid that renders in preview, and type any runtime.
- Saving commits to git; version history comes from git.
- The graph and search are projections rebuilt from files; no separate authoring.
- All 6 eval agents run and aggregate, offline (rules) and with a provider (LLM).
- No hardcoded runtime; no hardcoded LLM provider.
- No half-finished modules in scope; backend + frontend tests pass.

---

# Round 2 — Corrections & agentic evaluation (2026-06-29)

User feedback after round 1, with co-designed decisions:

1. **Remove the leftover "Import OKF" system.** The Knowledge Graph page was still
   wired to the legacy OKFDocument import (`/knowledge/okf/import`, `okf_service`,
   `OkfGraphRepository`). Remove that whole path. The Knowledge Graph page instead
   shows the **selected workspace's concept projection** (nodes + REFERENCES edges)
   plus semantic search — no import (files are the bundle).
2. **Finish/clean unfinished code:** delete the legacy OKFDocument import system,
   the legacy skills backend (router/service/repo/cypher + the `/evaluate` 501),
   and the `NotImplementedError` Celery stubs; replace with a real
   `reindex_workspace` task.
3. **Runtime is not hardcoded:** the editor's runtime AutoComplete is populated
   from the **distinct runtimes already in use** in the workspace, and remains
   free text so users can add new ones.
4. **Linked concepts — prompted helper:** an "Insert link" helper in the body
   editor. It is a guided picker (searchable list of workspace concepts +
   suggested related concepts) that inserts a bundle-root markdown link
   `[Title](/path.md)` at the cursor; the graph edge and "Linked concepts" list
   follow automatically.
5. **Agentic Deep evaluation (LLM-as-judge):** a **separate** on-demand run,
   distinct from the 6 fast rule checks. Flow: the LLM generates N test cases +
   edge cases for the skill → answers each **with** the skill body as context and
   **without** it → an LLM judge scores both → report **effectiveness** (with-vs-
   without delta + win-rate) and a per-case breakdown. Requires a chat-capable
   provider; with the local/offline provider it returns a clear "unavailable"
   result. The evaluator takes the provider by injection so it is testable with a
   stub provider.
