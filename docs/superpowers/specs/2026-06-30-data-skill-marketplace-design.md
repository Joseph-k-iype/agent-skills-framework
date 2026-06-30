# Data Skill Marketplace — Design Spec

**Date:** 2026-06-30
**Branch:** `feat/eakso-phase-0-3` (continuing)
**Status:** Approved — ready for implementation planning

## 1. Summary

Re-position the EAKSO app as **Data Skill Marketplace**: a public, creator-driven
marketplace for data skills (OKF concepts), with three clearly separated surfaces,
AI-assisted skill authoring, content-addressed (SHA) skill identity with versioning,
ratings/reviews, and a professional UI uplift on the existing Swiss-minimal palette.

Much of the substrate already exists (3-tier RBAC, marketplace listings, API keys,
mermaid rendering, OKF concept model, FalkorDB graph, LLM/eval pipelines). This work
sharpens separation, adds the missing capabilities, and lifts the UX — it is **not** a
rewrite.

## 2. Decisions (locked with user)

- **Who authors:** Any registered user. Self-serve creator platform. Default signup
  role grants authoring + API keys + publish.
- **Marketplace access:** Public, unauthenticated browse + skill detail. Login required
  only to *use/install*, generate keys, or author.
- **SHA identity:** Content-addressed integrity + version pin. SHA is computed per
  published version over canonical skill content; immutable per version.
- **AI assist:** All four forms — scaffold-from-prompt, inline rewrite/slash-commands,
  side-panel chat assistant, diagram generation. Uses the LLM provider/model already
  configured for eval pipelines (provider-agnostic via existing abstraction).
- **Marketplace features:** Categories/collections + tag browse, ratings & reviews,
  versions & changelog, one-click consume.
- **Visual direction:** Approved hybrid — keep original palette (Tesla Red `#E82127`
  accent used sparingly, warm off-white `#FAFAF8` canvas), editorial serif headlines +
  monospace SHA badges, warmed with soft card elevation, category pill chips, author
  avatar+handle, star ratings, `⌘K` search. Borrowed patterns from MCP Market
  (⌘K, one-click install, toolkits/bundles, API tokens, usage dashboard) and Cyrus
  (icon category strip, Featured curated row, author handle on cards).
- **Quality bar:** Enterprise-grade. Phased, tested, verified delivery.

## 3. Surfaces & access model

Three surfaces, each with its own layout:

1. **Public Marketplace** (no auth) — home (Featured + Trending + category strip),
   `⌘K`/full search, browse by category/tag with facets + sort, skill detail page.
   "Use skill" and any write action redirect to login.
2. **Creator Studio** (any registered user) — My Skills, the AI-assisted editor,
   drafts → publish, Toolkits, API Keys, public profile, usage of own skills.
3. **Admin Console** (admin role) — Dashboard/analytics (today's Insights), user & role
   management, marketplace moderation (feature/unfeature, takedown, review moderation),
   audit log.

### Role model

Keep the existing 3-tier RBAC table to minimize migration, re-scoped:

- **Default new signups → `developer`** (the creator role) so anyone can author.
- `consumer` retained for downgraded/suspended accounts (browse + use only).
- `admin` unchanged (superset) + gains marketplace moderation.
- New permissions: `assist:use` (creator), `review:write` (any logged-in user),
  `marketplace:moderate` (admin — may already exist; confirm).
- Public marketplace read endpoints require **no** permission (unauthenticated).

## 4. SHA identity & versioning

- On **publish**, compute `content_sha = sha256(canonical(skill))` where `canonical`
  is a deterministic serialization: normalized frontmatter (sorted keys, trimmed) +
  normalized body (LF newlines, trailing-whitespace-stripped). Volatile/derived fields
  (downloads, timestamps) are excluded.
- `content_sha` is **immutable per version**. Re-publishing changed content creates a
  **new version** (monotonic integer `v1, v2, …` plus optional semver label) with a new
  SHA and a changelog note. Identical content re-published is a no-op (same SHA).
- New table `skill_version`: `id`, `listing_id`, `version`, `content_sha`,
  `changelog`, `content` (frozen snapshot of frontmatter+body at publish), `published_at`,
  `downloads`. The `MarketplaceListing` points at its latest version and aggregates.
- SHA is surfaced as `sha[:7]` in UI, full `sha256:` in API/detail.
- Uses: short URL `/s/{sha}`, API consume by SHA, install/version pin, citation,
  **integrity verification on fetch** (recompute and compare → `409` on mismatch).

## 5. AI-assisted authoring

**Backend** — new `/assist` router using the existing provider abstraction and the
eval-configured model. Server owns all prompt templates (never trust client prompts).
Streaming via SSE where useful. Per-user rate limit + token ceiling; honest graceful
degradation when the LLM is unavailable (mirror existing deep-eval "honest skip").

- `POST /assist/scaffold` `{description, type?}` → structured draft
  `{frontmatter, body, mermaid}`.
- `POST /assist/rewrite` `{selection, command, context?}` → rewritten text. Slash-commands
  map to server-side instructions: `/improve`, `/expand`, `/condense`, `/fix-structure`,
  `/tighten`, `/rephrase`.
- `POST /assist/chat` `{messages, skill_context}` → streamed reply; may propose edits as
  fenced diff blocks the editor can apply.
- `POST /assist/diagram` `{description, existing?}` → mermaid block. Client renders;
  on mermaid parse error the editor sends the error back for one self-correction round.

**Frontend** — extend `ConceptEditorPage` into a three-pane **Studio editor**:

- Left: metadata form (title/type/runtime/tags/capabilities).
- Center: markdown editor with a **slash-command menu** and a **selection toolbar**
  (improve/expand/condense/fix). AI edits arrive as accept/reject diffs.
- Right: tabbed panel — **Preview** (existing `MarkdownPreview` + mermaid) | **Assistant**
  (chat) | **Evaluate** (existing fast/deep/grade).
- "Scaffold with AI" entry on new-skill creation.

## 6. Marketplace features

- **Discovery:** category strip (icon + count), tag facets, sort
  (Trending / Most used / Newest / Top rated), Featured curated row, Trending computed
  from recent `usage_event`s.
- **Ratings & reviews:** new `review` table (`listing_id`, `user_id`, `rating` 1–5,
  `body?`, `created_at`; one per user per skill, editable). Aggregate rating + count on
  cards and detail. Admin moderation.
- **Versions & changelog:** version selector + changelog on detail page; install a
  specific version/SHA.
- **One-click consume** (detail page action panel): clone-to-workspace, API snippet
  (`curl` with `sk_live_…` + `sha256`), SDK snippet — each with copy button.
- **Toolkits** (bundles, MCP-Market style): group several skills into one consumable
  unit. **Deferred to a later phase** to protect core scope (see §10).

## 7. Rename & branding

- Backend `core/config.py`: `app_name = "Data Skill Marketplace"` (drives FastAPI title +
  OpenAPI).
- Frontend: `SidebarLayout` wordmark, public top-nav wordmark, `package.json` name,
  document `<title>`, login page. Keep `tokens.ts` palette unchanged.

## 8. UI uplift

- New **public layout** (top-nav, no sidebar) distinct from the authed Studio/Admin
  sidebars.
- Rebuild marketplace home + detail to the approved hybrid (cards with serif headline,
  category pill, tags, author avatar+handle, ★ rating, usage, monospace SHA badge,
  ink-black primary action so red stays special).
- `⌘K` command-palette search component.
- Nav restructure: public top-nav; Studio sidebar (My Skills, Editor, Toolkits, API Keys,
  Profile); Admin sidebar (Dashboard, Users, Roles, Moderation, Audit).

## 9. Backend data model & API changes

- `skill_version` table (§4); `MarketplaceListing` extended with `category`, `featured`,
  latest-version pointer, aggregate rating.
- `review` table (§6).
- New **public** (unauth) router `/public/marketplace*` and `/public/skills/{sha}` —
  serves only published content, rate-limited, never leaks drafts.
- `/assist/*` router (§5).
- Reuse existing `usage_event` for trending; existing API keys unchanged.

## 10. Phasing (incremental, each phase tested + verified)

- **Phase 1 — Foundation:** rename + branding; SHA identity + `skill_version` model +
  publish pipeline; public (unauth) marketplace read API; palette-correct marketplace
  home + detail UI uplift; public layout. *(Ships a coherent, demoable slice.)*
- **Phase 2 — AI-assisted editor:** `/assist/*` backend; three-pane Studio editor with
  scaffold, slash-commands/selection rewrite, chat panel, diagram generation.
- **Phase 3 — Marketplace depth:** ratings & reviews; versions/changelog UI; one-click
  consume (clone / API / SDK snippets).
- **Phase 4 — Surface separation & admin:** finalize Studio vs Admin vs Public layouts +
  nav; moderation tools (feature/takedown/review moderation); audit surfacing.
- **Phase 5 (optional) — Toolkits/bundles.**

## 11. Testing & verification

- **Backend:** pytest via `uv run --python 3.12 --with …` (per project memory). New tests:
  SHA canonicalization determinism + idempotent re-publish; public endpoints reject draft
  leakage and require no auth; review CRUD + one-per-user constraint; `/assist/*` contract
  tests with a mocked LLM provider; integrity-mismatch `409`.
- **Frontend:** component/render tests where the harness supports them; manual verification
  by running the app (the `run`/`verify` flow) for each phase's UI.
- **Per-phase gate:** tests green + manual smoke before moving on. No phase merges on
  assertion-without-evidence.

## 12. Error handling

- AI-assist: LLM-unavailable → honest degraded response (no fabricated success), explicit
  rate-limit `429`, streamed error frames the editor surfaces inline.
- SHA: fetch integrity mismatch → `409`; publish of identical content → no-op same SHA.
- Public endpoints: rate-limited; strict published-only filtering; no draft/workspace leak.

## 13. Out of scope (YAGNI for now)

- Payments/paid skills. Org/multi-tenant billing. Real-time collaborative editing.
- Email notification system. Public REST docs portal beyond snippet generation.
- Toolkits beyond Phase 5 stub if time-constrained.
