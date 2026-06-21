# Skill Documentation — Markdown Editor with Mermaid

**Date:** 2026-06-21
**Scope:** `frontend/` (React UI) + one new `frontend/api/` endpoint. Adds an authoring +
rendering experience for a skill's Markdown documentation (the body of `SKILL.md`), including
live-rendered Mermaid diagrams.

## Problem

A skill's documentation is the Markdown body of `SKILL.md` (everything after the YAML
frontmatter). Today the UI provides no way to author it (the Create wizard hardcodes a fixed
boilerplate body at `CreateSkill.tsx:114`) and the Skill Detail "Documentation" tab shows the
body as raw `whitespace-pre-wrap` text (`SkillDetail.tsx:269`) — Markdown and Mermaid are not
rendered. No markdown/mermaid libraries are installed.

## Key facts established

- **Editing the body does not change the skill ID.** `compute_skill_id` hashes the canonical
  frontmatter JSON (id stripped) plus the files from `iter_source_files`, which excludes
  manifests (`SKILL.md`). The Markdown body is therefore not part of the content hash, so
  editing it keeps `registry.verify()` passing. Docs are mutable metadata.
- `scaffold` (`skills.py:271`) already accepts `manifest.body` and writes it into the generated
  `SKILL.md`. The create flow only needs an editor wired to that field.
- `_parse_frontmatter` (`validation.py:28`) splits frontmatter from body; the closing delimiter
  is the first line equal to exactly `---`. The edit endpoint mirrors this to preserve the
  frontmatter block verbatim and replace only the body.

## Decisions (locked)

- **Surfaces:** author in Create wizard; edit docs for existing skills (new backend endpoint);
  render Markdown + Mermaid in the read view.
- **Editor UX:** tabbed Write / Preview (single full-width pane, toggled).

## Components (new — `frontend/src/components/markdown/`)

### `Mermaid.tsx`
- Lazy-loads `mermaid` via dynamic `import('mermaid')` so it is code-split out of the initial
  bundle (only loaded when a diagram is rendered).
- Initializes once with `{ startOnLoad: false, securityLevel: 'strict', theme: 'neutral' }`
  (or a light theme tuned to the palette).
- Renders the diagram source to SVG into a container; uses a unique id per instance.
- On parse/render error, renders the raw code in a bordered `bg-canvas` block plus the error
  message — never throws past an error boundary.

### `MarkdownPreview.tsx`
- `react-markdown` + `remark-gfm`. A custom `code` component renderer:
  - fenced ` ```mermaid ` → `<Mermaid chart={...} />`
  - other fenced code → highlighted via `rehype-highlight`
  - inline code → styled `<code>`
- No `rehype-raw` (raw HTML disabled) → XSS-safe for arbitrary doc content.
- Wrapped in a `prose` container themed to the ink palette via `@tailwindcss/typography`
  (light prose; configure `--tw-prose-*` to `ink`/`ink-2`/`line`/`accent`).

### `MarkdownEditor.tsx`
- Tabbed Write / Preview using existing `.tab` / `.tab-active`.
- **Write**: Monaco (`@monaco-editor/react`, already a dependency) with
  `defaultLanguage="markdown"`, `theme="light"`, sensible options (wordWrap on, minimap off).
- **Preview**: `MarkdownPreview` of the current value.
- Props: `value: string`, `onChange: (v: string) => void`, `height?: string`,
  `readOnly?: boolean`.

## Integration points

### Create wizard (`routes/CreateSkill.tsx`)
- Add a **Documentation** step between "Dependencies & Triggers" and "Review" (steps 4 → 5;
  update the progress indicator and step labels).
- Add `docBody` state seeded with the existing boilerplate template
  (`# {name}\n\n...Usage...Examples`).
- `MarkdownEditor` edits `docBody`.
- `buildManifestPayload()` sets `manifest.body = docBody` (remove the hardcoded template).
- `handleDownload()` uses `docBody` for the downloaded `SKILL.md`.

### Skill Detail (`routes/SkillDetail.tsx`)
- Documentation tab: render `manifestBody` with `MarkdownPreview` (replacing the raw
  `whitespace-pre-wrap` block). Fallback to `doc` when no `manifestBody`.
- Add an **Edit** button visible to users with `skill:create` (via `RequirePermission`). It
  swaps the tab into `MarkdownEditor` with **Save** and **Cancel**.
- Save calls `api.skills.updateDoc(name, body)`, then invalidates the `['manifest', name]`
  query and returns to preview.

## Backend (`frontend/api/routes/skills.py`)

New endpoint:

```
PUT /skills/{name}/doc        (dependencies=[Depends(require_api_key)])
body: { "body": str }
```

- Resolve `_skill_dir_or_404(name)` → `_manifest_path(skill_dir)`.
- If the manifest is not `SKILL.md` (legacy `skill.yaml/yml/json`) → 400
  "Documentation editing requires SKILL.md format".
- Read raw text; locate the closing frontmatter `---` line exactly as `_parse_frontmatter`
  does; rebuild as `<frontmatter block verbatim>\n\n<new body>\n` and write back atomically.
- Return `{ "body": <new body> }`.
- Caveat (documented, not handled): edits the registry's served copy; a later
  `sync_from_sources` from a source repo can overwrite it.

Frontend API client (`lib/api.ts`):

```
updateDoc: (name, body) => fetchJSON(`/skills/${name}/doc`, { method: 'PUT', body: JSON.stringify({ body }) })
```

Add any needed type to `lib/types.ts`.

## Libraries to add

`react-markdown`, `remark-gfm`, `rehype-highlight`, `mermaid`, `@tailwindcss/typography`
(dev). Configure the typography plugin in `tailwind.config.js` and import a highlight.js CSS
theme (light) in `index.css`. Mermaid is dynamically imported, so it does not enter the main
chunk.

## Security

- No raw HTML rendering (no `rehype-raw`).
- Mermaid `securityLevel: 'strict'`.
- Edit endpoint behind `require_api_key`; UI behind `skill:create`.

## Testing

- **Backend pytest** (`frontend/api/tests/`): PUT writes the body; frontmatter preserved
  byte-for-byte; recomputed skill ID unchanged after an edit; legacy manifest → 400.
- **Frontend vitest**: `MarkdownPreview` renders headings/bold/lists and routes a ` ```mermaid `
  fence to the Mermaid component (mermaid module mocked).
- **Manual**: author docs in the create wizard; edit + save docs on an existing skill; confirm a
  Mermaid diagram renders (screenshot).

## Out of scope

- Versioning/history of doc edits.
- Editing the original source repo copy (only the served registry copy is written).
- Image upload/asset management.
- Collaborative editing.

## Implementation order

1. Add libraries; configure typography plugin + highlight CSS.
2. `Mermaid.tsx` → `MarkdownPreview.tsx` → `MarkdownEditor.tsx`.
3. Backend `PUT /skills/{name}/doc` + pytest.
4. `api.ts` `updateDoc` + types.
5. Wire SkillDetail Documentation tab (render + edit).
6. Wire CreateSkill Documentation step.
7. Verify: pytest, vitest, build, manual walkthrough.
