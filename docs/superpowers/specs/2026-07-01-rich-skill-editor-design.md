# Rich Skill Editor — Design Spec

**Date:** 2026-07-01
**Branch:** `feat/rich-skill-editor`
**Status:** Approved (pending spec review) — ready for implementation planning
**Builds on:** the existing markdown concept editor (`ConceptEditorPage`), `MarkdownPreview`
(GFM + Mermaid), and the graph-edge model where markdown links become `references`.
**Roadmap position:** Workstream **A** of a six-part marketplace build
(A rich editor → B per-skill stats/clone → C home ranking + lazy load →
D OTel/Grafana observability → E framework adapters → F design studio). Each
subsequent workstream gets its own spec.

## 1. Summary

Turn the plain markdown `<textarea>` in the skill editor into a **rich authoring
surface** — a Monaco-based markdown editor with a formatting **toolbar**, a `/`
**slash-command** insert menu, **Mermaid** diagram templates, and **sanitized raw
HTML** rendering in preview. Markdown remains the stored format, so the OKF
graph-edge extraction (`[title](/path)` → `references`) is unchanged. The live
split preview is kept and hardened. Subtle, fast motion polish is added to the
editor; the heavier animation library is deferred to workstream C (home/browse).

## 2. Decisions (locked with user)

- **Editing surface:** **Monaco** (`@monaco-editor/react` + `monaco-editor`),
  lazy-loaded, markdown language, with a formatting toolbar and a `/` slash menu.
  Markdown stays the source of truth (WYSIWYG-to-HTML was explicitly rejected to
  preserve graph-edge extraction).
- **Raw HTML:** **render, sanitized** — add `rehype-raw` + `rehype-sanitize` to the
  preview. Scripts, event-handler attributes, and `javascript:` URLs are stripped;
  a curated tag/attribute allowlist (plus an iframe-src allowlist for embeds) is
  permitted.
- **Fancy motion:** **home/browse AND editor**, but the editor gets only *subtle,
  fast* polish (save confirmation, count ticker, panel reveals) via a small local
  util set. The full fancycomponents-style library is a workstream-C concern.

## 3. Architecture & source of truth

The stored value is still `concept.body` (markdown). Every formatting action is a
**pure text transform**, so the logic is unit-testable without a browser:

- `features/concepts/lib/markdownTransforms.ts` — `toggleBold`, `toggleItalic`,
  `toggleStrikethrough`, `toggleInlineCode`, `setHeading(level)`,
  `toggleBulletList`, `toggleNumberedList`, `toggleChecklist`, `toggleQuote`,
  `insertCodeBlock(lang?)`, `insertTable(rows, cols)`, `insertLink(text, href)`,
  `insertImage(alt, src)`, `insertHtmlBlock()`. Each takes `(text, selection)` and
  returns `{ text, selection }`.
- `features/concepts/lib/mermaidTemplates.ts` — `mermaidTemplate(kind)` for
  `flowchart | sequence | class | state | er | gantt`, returning a ready-to-edit
  fenced ```mermaid block.
- `features/concepts/lib/slashCommands.ts` — the declarative command list
  (label, keywords, insert action) shared by the toolbar and the slash menu.

Monaco is the *surface* that applies these transforms via `editor.executeEdits()`
and selection APIs. It never owns formatting logic.

## 4. Editor surface — Monaco

- New component `features/concepts/components/editor/SkillEditor.tsx`
  (`{ value, onChange, onCursorChange }`), wrapping `@monaco-editor/react`.
- **Lazy-loaded** via `React.lazy` / dynamic import so `monaco-editor` is a
  separate Vite chunk and does not bloat initial load. A `<Suspense>` skeleton
  covers first load.
- Markdown language: syntax highlight, bracket matching, multi-cursor, word wrap on.
- Theme derived from `tokens` to match the Swiss storefront look (light theme,
  mono font).
- `SkillEditor` exposes an imperative handle (`applyTransform(fn)`) so the toolbar
  and slash menu apply pure transforms against the current selection.

## 5. Feature set

**Toolbar** (`features/concepts/components/editor/EditorToolbar.tsx`): bold, italic,
strikethrough · H1/H2/H3 · bullet / numbered / checklist · quote · inline code ·
code block · **link** (two actions: *concept link* → reuses the existing graph-edge
picker modal; *external link* → prompt for URL) · **table** (R×C picker) ·
**Mermaid** (dropdown of the six templates) · image · **HTML block**.

**Slash menu** (`/`): a Monaco `CompletionItemProvider` registered for markdown,
sourced from `slashCommands.ts`. Commands mirror the toolbar plus templates:
`/table`, `/mermaid <kind>`, `/code`, `/callout`, `/h1..h3`, `/link`, `/html`,
`/skill-template` (a starter SKILL.md scaffold). Selecting a command applies the
same pure transform the toolbar uses.

**Mermaid templates:** inserting a type drops a valid fenced block that renders
live in preview (rendering already works today).

**Concept links stay graph edges:** the existing "Insert link" modal is preserved
and surfaced from the toolbar; inserted `[title](/path)` links still become
`references` on save. No change to link semantics.

## 6. Preview — sanitized HTML

`MarkdownPreview` gains, in order, `remark-gfm` → `rehype-raw` → `rehype-sanitize`:

- `rehype-raw` parses embedded HTML into the tree.
- `rehype-sanitize` runs with a customized schema: default-safe allowlist extended
  with common presentational tags/attrs (e.g. `div`, `span`, `details`, `summary`,
  class usage) and an **iframe allowlist** restricting `src` to an approved host set
  (e.g. youtube/vimeo embeds) — configurable in one place.
- Mermaid code-fence handling is preserved (the existing `code` component override
  runs after sanitize; mermaid source is our own render path, not raw HTML).

Security is the sensitive change here, so it gets dedicated tests: `<script>`,
`onerror=`, `javascript:` hrefs, and disallowed iframe hosts must all be stripped,
while allowed markup survives.

## 7. Layout, view modes & subtle motion

- **View modes:** an **Edit / Split / Preview** segmented toggle. Split is default on
  wide screens; narrow screens (`!screens.lg`) default to single-pane Edit with the
  toggle. Optional **Zen/fullscreen** mode that expands the editor.
- **Subtle motion** (local `features/shared/fancy/`, CSS/RAF-based, no heavy dep):
  animated **save confirmation**, a **number ticker** on the live word/char count,
  and a smooth reveal when switching view modes. Kept lightweight so typing stays
  responsive.
- These live in the existing "Editor" tab of `ConceptEditorPage`; the other tabs
  (Metadata, Linked concepts, Evaluate, Deep eval, Test cases, History) are unchanged.

## 8. Testing

Follows the repo's `features/concepts/__tests__` + Vitest convention, TDD-first:

- **Pure transforms** (`markdownTransforms`, `mermaidTemplates`, `slashCommands`):
  full unit coverage of text/selection results — the bulk of the logic.
- **Sanitize** (`MarkdownPreview`): XSS payloads stripped, allowed markup + mermaid +
  GFM tables preserved.
- **SkillEditor / toolbar:** Monaco is mocked (it does not run in jsdom); a light
  smoke test verifies toolbar actions call `applyTransform` with the right transform
  and that the slash-command list is wired.

## 9. New dependencies

`@monaco-editor/react`, `monaco-editor`, `rehype-raw`, `rehype-sanitize`.
(Mermaid, react-markdown, remark-gfm already present.)

## 10. Risks & mitigations

- **Monaco bundle size** → lazy-load + dedicated Vite chunk; Suspense skeleton.
- **Monaco ≠ jsdom** → extract all logic into pure functions; mock Monaco in tests.
- **HTML XSS** → `rehype-sanitize` with an explicit, centralized allowlist + payload
  tests; iframe src restricted to an approved host list.
- **Overlap with the Phase 2 AI-assisted authoring spec** (which also adds slash
  commands / diagram generation) → this editor's `slashCommands.ts` is the single
  registry both features extend; AI "rewrite" commands slot into the same menu
  rather than a parallel one.

## 11. Out of scope (future workstreams)

Per-skill download history / clone (B), home ranking + infinite scroll and the full
fancycomponents library (C), OTel/Grafana usage observability (D), framework
adapters — LangGraph/LangChain/ADK/Claude/Copilot (E), and the composed design
studio (F).
