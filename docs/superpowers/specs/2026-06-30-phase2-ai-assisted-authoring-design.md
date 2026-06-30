# Phase 2 — AI-Assisted Authoring — Design Spec

**Date:** 2026-06-30
**Branch:** `feat/eakso-phase-0-3` (continuing)
**Status:** Approved (pending spec review) — ready for implementation planning
**Builds on:** Phase 1 (SHA versioning, public marketplace) + the Swiss storefront uplift.

## 1. Summary

Add AI assistance to the skill editor so any registered user can author high-quality
data skills fast. Four assist modes — **scaffold from a prompt**, **inline rewrite /
slash-commands**, a **side-panel chat assistant**, and **diagram generation** — backed
by a new server-side `/assist` API that calls a capable Claude model through the
existing OpenRouter provider. AI never edits silently: changes land as an
**accept/reject diff**.

## 2. Decisions (locked with user)

- **Model:** a capable Claude (Sonnet-class) model via OpenRouter, behind a new
  configurable `assist_model` setting. Evals keep their current free model. (Exact
  model id pinned from the claude-api reference at implementation.)
- **Scope:** all four assist modes this phase, built/reviewed as four sequential slices.
- **Edit UX:** accept/reject diff — nothing touches the document until the author accepts.
- **Chat:** request/response (non-streaming) this phase; token-streaming is a fast-follow.
- **Authoring access:** default new-signup role → `developer`; new `assist:use` permission
  (developer + admin).

## 3. Backend — `/assist` router

New router `backend/app/api/v1/routers/assist.py`, registered under `/assist`, all
endpoints requiring the `assist:use` permission. The server owns ALL prompt templates
(in a new `backend/app/assist/prompts.py`); the client never supplies system prompts.

- `POST /assist/scaffold` `{description, type?}` → `{frontmatter: dict, body: str, mermaid: str|null}`
  (structured; the model is instructed to return parseable JSON, validated server-side).
- `POST /assist/rewrite` `{selection, command, context?}` → `{rewritten: str}`. `command`
  is one of a fixed server-side set mapping slash-commands to instructions:
  `improve`, `expand`, `condense`, `fix-structure`, `tighten`, `rephrase`.
- `POST /assist/chat` `{messages: [{role, content}], skill_context}` → `{reply: str}`.
  The reply may contain proposed edits as fenced ```diff blocks the editor can surface
  for accept/reject. Request/response (non-streaming) this phase.
- `POST /assist/diagram` `{description, existing?}` → `{mermaid: str}`. The client renders
  it via the existing `MarkdownPreview`; on a mermaid parse error the client re-POSTs once
  with the error text for a single self-correction round.

**Service layer:** `backend/app/services/assist_service.py` assembles prompts, calls the
provider, validates/normalizes output, and enforces guardrails. **Provider:** extend the
existing LLM provider abstraction (`app/llm/providers/`) with a `chat(messages, *, model)
-> str` method if not already present; the OpenRouter provider implements it. Config gains
`assist_model: str` (default a Claude Sonnet OpenRouter id).

**Guardrails / error handling:**
- `assist:use` permission required (401/403 otherwise).
- A light per-user rate limit (in-process token-bucket keyed by user id) → `429` with a
  clear "slow down" envelope when exceeded.
- Per-request output token ceiling.
- LLM unavailable / provider error / over budget → an **honest degraded response**
  (mirrors the existing deep-eval "honest skip": a structured `{ok: false, reason}`),
  never fabricated content. The editor surfaces this as a non-blocking notice.

## 4. Frontend — three-pane Studio editor

Extend `frontend/src/features/concepts/pages/ConceptEditorPage.tsx` into a three-pane
Studio editor (keeping the existing save/publish → SHA-versioning flow from Phase 1):

- **Left:** the existing metadata form (title/type/runtime/tags/capabilities) — unchanged.
- **Center — the markdown editor**, augmented with:
  - A **slash-command menu**: typing `/` opens a menu of rewrite commands that act on the
    current selection (or current section if no selection).
  - A **selection toolbar**: selecting text shows a small floating toolbar
    (Improve / Expand / Condense / Fix).
  - **Accept/reject diff review**: every AI edit (rewrite, scaffold, chat-proposed edit)
    is presented as a before→after diff for the affected range in a review affordance;
    Accept applies it to the document, Reject discards. Implemented as a diff panel/modal
    (not inline editor decorations) so it works with the current editor component.
- **Right — a tabbed panel:** **Preview** (existing `MarkdownPreview` + mermaid) |
  **Assistant** (the chat panel — messages + input; assistant replies can include a
  proposed edit the author accepts/rejects) | **Evaluate** (existing fast/deep/grade).
- **"Scaffold with AI"** entry on new-skill creation: a prompt box → `POST /assist/scaffold`
  → the generated draft (frontmatter + body + optional mermaid) is presented as a diff/accept
  before it populates the editor.
- **"Generate diagram"** action: describe a flow → `POST /assist/diagram` → inserts a mermaid
  block (live-rendered by `MarkdownPreview`, which already surfaces mermaid errors), with the
  one-round fix-on-error loop.

New frontend module `frontend/src/features/concepts/assist/` holds the assist API client,
the slash-command + selection-toolbar components, the diff-review component, and the chat
panel — each a focused unit so the editor page stays readable.

## 5. Roles / permissions

- Add `assist:use` to the permission catalog (`backend/app/auth/rbac.py`), granted to
  `developer` and `admin`.
- Change the default role assigned to new local/LDAP-unmapped users from `consumer` to
  `developer` (`backend/app/auth/service.py`), so any registered user can author + use
  assist. (Resolves the deferred Phase-1 "default signup = developer" item.)

## 6. Data flow

Editor action → `POST /assist/*` (JWT, `assist:use`) → `AssistService` assembles the
server-owned prompt → provider `chat(messages, model=assist_model)` (Claude via OpenRouter)
→ validated structured result → editor shows it as a diff / chat reply → author accepts →
editor document updated → existing save/publish path (computes the content SHA, appends a
`SkillVersion` per Phase 1).

## 7. Testing

- **Backend:** `/assist/*` contract tests with a **mocked provider** (no real LLM in tests):
  assert prompt assembly uses the server templates, the structured output shapes
  (`scaffold`/`rewrite`/`chat`/`diagram`), `assist:use` is required, the rate-limit `429`,
  and graceful degradation when the provider raises. A unit test for the slash-command →
  instruction mapping. Run via `cd backend && uv run --python 3.12 pytest`.
- **Frontend:** vitest + RTL component tests for the slash-command menu (opens on `/`,
  lists commands), the selection toolbar (appears on selection), and the diff-review
  accept/reject (Accept applies, Reject leaves the doc unchanged). Manual verification of
  end-to-end assist quality against the real model.

## 8. Build sequence (within this phase — each a reviewable slice)

1. **Backend `/assist` foundation + scaffold:** config `assist_model`, provider `chat`,
   prompts module, `AssistService`, the router, `assist:use` permission, default-role
   change; `POST /assist/scaffold` + the "Scaffold with AI" entry and its diff-accept.
2. **Inline rewrite + slash-commands + diff review:** `POST /assist/rewrite`, the
   slash-command menu, the selection toolbar, and the accept/reject diff component.
3. **Chat panel:** `POST /assist/chat` + the Assistant tab (messages, input, propose-edit
   → accept/reject).
4. **Diagram generation:** `POST /assist/diagram` + the "Generate diagram" action and the
   one-round fix-on-error loop.

## 9. Out of scope (YAGNI)

- Token-streaming (SSE) — fast-follow after this phase.
- Autonomous "write the whole skill and publish without review"; multi-file/agentic editing.
- Voice input; real-time collaborative editing; fine-tuning / custom models.
- Cross-skill RAG over the catalog inside the editor (possible later phase).

## 10. Error handling summary

- LLM down / over budget → honest `{ok:false, reason}` surfaced as a notice; no fabrication.
- Rate limit → `429` with a clear message.
- Invalid mermaid from `/assist/diagram` → one auto-fix round, then show the error inline
  (existing `MarkdownPreview` behavior).
- Malformed model JSON (scaffold/rewrite) → server validates and retries once with a
  stricter instruction; on second failure returns an honest error, not partial garbage.
