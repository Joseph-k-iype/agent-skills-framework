# Frontend Redesign — Light Theme ("Instrument")

**Date:** 2026-06-21
**Scope:** `frontend/` React + Vite + Tailwind UI. Purely presentational. No backend, data, routing, or business-logic changes.

## Goal

Replace the current dark, indigo-accented UI with a light-first design that blends Apple's
warmth (generous whitespace, soft depth, refined type) with Tesla's precision (monochrome ink
palette, crisp 1px hairlines, restraint). A single sharp red accent carries meaning — primary
action, active state, the one headline figure — and is used rarely. The result should read as
deliberate and crafted, not as a templated SaaS dashboard.

## Direction decisions (locked)

- **Aesthetic:** balanced hybrid — Apple warmth + Tesla precision.
- **Accent:** near-monochrome base + a single Tesla-style red accent, used sparingly.
- **Theme:** light-only. The existing dark theme is removed (not toggled). Dark mode may be
  re-added later but is out of scope here.
- **Coverage:** full redesign — design tokens, app shell, and all route pages.

## Anti-cliché constraints

- No four-color icon chips (the current Dashboard pattern).
- No indigo / blue-to-purple gradient SaaS look.
- No heavy drop shadows. Structure reads through whitespace and hairlines; depth is subtle
  (stone canvas + pure-white surfaces).
- Red is an event, never a background fill.

## Design tokens

### Color (light)

| Token        | Value                | Use                                          |
|--------------|----------------------|----------------------------------------------|
| `canvas`     | `#F6F6F4` warm stone | app background                               |
| `surface`    | `#FFFFFF`            | cards, panels, topbar                        |
| `ink`        | `#0E0E10`            | primary text, headings                       |
| `ink-2`      | `#6B6B70`            | secondary text                               |
| `ink-3`      | `#9A9AA0`            | tertiary / meta                              |
| `line`       | `#E7E7E3`            | hairline borders and dividers                |
| `accent` red | `#E5301E` (50→900 scale) | primary CTA, active nav, single key figure |
| state colors | desaturated emerald / amber / rose | status **dots** only, never fills |

Implemented as Tailwind theme extensions. The red gets a full 50–900 scale so hover/active/
focus tints are available. State colors stay muted and are used only as small indicator dots.

### Typography

- **Primary font:** Geist (geometric, neutral, precise), with system-font fallback stack.
- **Mono font:** Geist Mono for skill IDs, content hashes, versions.
- Fonts self-hosted via `@fontsource/geist-sans` + `@fontsource/geist-mono` (added to
  `package.json`), imported in `index.css`. (Fallback: if package install is undesirable, use
  the Apple system stack `-apple-system, BlinkMacSystemFont, ...` — one-line swap.)
- **Headings:** medium weight, tight letter-spacing, larger scale.
- **Eyebrow labels:** small, uppercase, wide tracking for section headers.
- **Body:** regular weight, comfortable line-height.

### Shape, depth, motion

- Border radius: `~12px` (rounded-xl) for cards/panels, `~8px` for buttons, full for pills.
- Shadows: a single very soft, low-opacity elevation token for hover/active only.
- Motion: 150–200ms ease transitions; tiny hover lifts; no bounce.

## Component spec

All shared component classes live in `frontend/src/index.css` under `@layer components`.

- **`.card` / `.card-hover`** — white surface, `line` hairline border, generous padding; hover
  adds a soft shadow + slightly darker border.
- **`.btn-primary`** — solid red, white text; hover/active use red scale steps.
- **`.btn-secondary`** — white with ink hairline outline; subtle gray hover.
- **`.btn-ghost`** — transparent; subtle gray hover.
- **`.input`** — white, hairline border, thin red focus ring, taller target.
- **`.badge` / `.tag`** — light gray pills with ink text.
- **`.eyebrow`** (new) — uppercase, wide-tracked, small, `ink-3` section label.
- **`.tab` / `.tab-active`** — ink text, red underline for active.
- **Focus state** — `:focus-visible` uses the red accent outline.

## Shell

- **Sidebar** (`components/layout/Sidebar.tsx`) — stone/white background, hairline right border,
  monochrome icons. Active item: ink text + thin red left indicator bar. Logo replaced with a
  monochrome ink mark (no indigo square). Version pill in `ink-3`.
- **TopBar** (`components/layout/TopBar.tsx`) — frosted translucent (`backdrop-blur`) sticky bar,
  hairline bottom border. Search rendered as a quiet pill. "New Skill" is the red primary button.
- **AppShell** (`components/layout/AppShell.tsx`) — canvas background, comfortable content padding,
  sensible max content width for readability.

## Route pages (all restyled, logic unchanged)

`Dashboard`, `SkillCatalog`, `SkillDetail`, `Registry`, `KnowledgeGraph`, `Governance`,
`Deployments`, `AuditLog`, `Settings`, `CreateSkill`, `NotFound`.

Shared components also restyled: `InstallModal`, `EvaluationPanel`, `ErrorBoundary`,
`RequireRole`.

- Replace every dark utility (`bg-gray-9xx`, `text-gray-1xx`, `border-gray-8xx`, `brand-*`, etc.)
  with the new tokens.
- **Dashboard stat cards** reworked: large light numerals + small uppercase labels, monochrome,
  with red reserved for the single headline metric. The four colored icon chips are removed.
- Lists/tables: airy rows separated by hairline dividers.

## Out of scope

- Backend / API, data shapes, routing, auth, and business logic.
- Dark mode.
- New features or content. Component structure changes only where needed for the visual system.

## Testing & verification

- Existing Vitest component tests assert on text/roles/structure, not colors — they must keep
  passing. Run `cd frontend && npm test`.
- Manual verification: run the dev server, walk each route, confirm the light theme, red accent
  usage, hairline structure, and that no dark remnants remain.
- Type-check / build must succeed (`npm run build`).

## Implementation order

1. Tokens: `tailwind.config.js` (colors, fonts, radius, shadow).
2. Fonts: add `@fontsource` deps, import in `index.css`, update `index.html`.
3. Global component classes: `index.css` `@layer base` + `@layer components`.
4. Shell: `AppShell`, `Sidebar`, `TopBar`.
5. Pages: Dashboard first (reference), then remaining routes.
6. Shared components: modals, panels, boundaries.
7. Verify: tests, build, manual walkthrough.
