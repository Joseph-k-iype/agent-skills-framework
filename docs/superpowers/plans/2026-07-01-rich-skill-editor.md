# Rich Skill Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain markdown `<textarea>` in the skill editor with a Monaco-based rich authoring surface — formatting toolbar, `/` slash-command menu, Mermaid templates, sanitized raw-HTML preview, and Edit/Split/Preview view modes with subtle motion — while keeping markdown as the stored format so graph-edge extraction is unchanged.

**Architecture:** All formatting logic lives in **pure functions** (`markdownTransforms`, `mermaidTemplates`, `slashCommands`) that take `(text, selection)` and return `{ text, selection }`. Monaco is only the surface that applies them. Preview gains `rehype-raw` + `rehype-sanitize`. The editor is composed into the existing `ConceptEditorPage` "Editor" tab; all other tabs are untouched.

**Tech Stack:** React 18, TypeScript 5.5, Vite 5, Vitest 2 + Testing Library, antd 5, `@monaco-editor/react` + `monaco-editor` (new), `react-markdown` + `remark-gfm` (present), `rehype-raw` + `rehype-sanitize` (new), `mermaid` (present).

## Global Constraints

- **Working directory for all frontend commands:** `frontend/` (run `cd frontend` first).
- **Markdown is the stored format.** Never change `concept.body` to HTML. Concept links `[title](/path)` MUST remain intact — they become graph edges on save.
- **Pure functions own all formatting logic.** Monaco never contains transform logic; it calls transforms. This keeps logic testable in jsdom (Monaco does not run in jsdom and MUST be mocked in tests).
- **Selection model:** `Sel = { start: number; end: number }` are character offsets into the markdown string.
- **Design tokens:** import from `@/app/theme/tokens`. Accent `#E82127`, ink `#111114`, line `#ECECE8`, surface `#FFFFFF`, canvas `#FAFAF8`, mono font `tokens.font.mono`.
- **Test command:** `npx vitest run <path>` for a single file; `npm test -- run` for all. **Typecheck:** `npx tsc --noEmit`. **Lint:** `npm run lint` (if present). **Build:** `npm run build`.
- **Commit** after every task with a `feat(editor):` / `test(editor):` scoped message. Branch is already `feat/rich-skill-editor`.

---

### Task 1: Pure markdown transforms

**Files:**
- Create: `frontend/src/features/concepts/lib/markdownTransforms.ts`
- Test: `frontend/src/features/concepts/lib/__tests__/markdownTransforms.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `type Sel = { start: number; end: number }`
  - `type TransformResult = { text: string; selection: Sel }`
  - `type Transform = (text: string, sel: Sel) => TransformResult`
  - Named transforms: `toggleBold`, `toggleItalic`, `toggleStrikethrough`, `toggleInlineCode`, `setHeading(level: 1|2|3): Transform`, `toggleBulletList`, `toggleNumberedList`, `toggleChecklist`, `toggleQuote`, `insertCodeBlock(lang?: string): Transform`, `insertTable(rows: number, cols: number): Transform`, `insertLink(label: string, href: string): Transform`, `insertImage(alt: string, src: string): Transform`, `insertHtmlBlock(): Transform`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/features/concepts/lib/__tests__/markdownTransforms.test.ts
import { describe, expect, it } from "vitest";
import {
  toggleBold,
  toggleItalic,
  setHeading,
  toggleBulletList,
  toggleQuote,
  insertTable,
  insertLink,
  insertHtmlBlock,
} from "../markdownTransforms";

describe("markdownTransforms", () => {
  it("wraps a selection in bold markers", () => {
    const r = toggleBold("the word", { start: 4, end: 8 });
    expect(r.text).toBe("the **word**");
    expect(r.text.slice(r.selection.start, r.selection.end)).toBe("word");
  });

  it("unwraps bold when the selection is already bold", () => {
    const r = toggleBold("the **word**", { start: 6, end: 10 });
    expect(r.text).toBe("the word");
  });

  it("inserts empty bold markers with the cursor between them", () => {
    const r = toggleBold("x", { start: 1, end: 1 });
    expect(r.text).toBe("x****");
    expect(r.selection).toEqual({ start: 3, end: 3 });
  });

  it("italic uses single asterisks", () => {
    expect(toggleItalic("word", { start: 0, end: 4 }).text).toBe("*word*");
  });

  it("setHeading prefixes the current line with hashes", () => {
    const r = setHeading(2)("hello", { start: 2, end: 2 });
    expect(r.text).toBe("## hello");
  });

  it("setHeading replaces an existing heading level", () => {
    expect(setHeading(1)("### hi", { start: 5, end: 5 }).text).toBe("# hi");
  });

  it("toggleBulletList prefixes each selected line", () => {
    const r = toggleBulletList("a\nb", { start: 0, end: 3 });
    expect(r.text).toBe("- a\n- b");
  });

  it("toggleQuote prefixes the line with a blockquote marker", () => {
    expect(toggleQuote("note", { start: 0, end: 0 }).text).toBe("> note");
  });

  it("insertTable inserts a GFM table skeleton", () => {
    const r = insertTable(2, 2)("", { start: 0, end: 0 });
    expect(r.text).toContain("| Column 1 | Column 2 |");
    expect(r.text).toContain("| --- | --- |");
  });

  it("insertLink wraps selected text as the link label", () => {
    const r = insertLink("Docs", "https://x.dev")("see Docs", { start: 4, end: 8 });
    expect(r.text).toBe("see [Docs](https://x.dev)");
  });

  it("insertHtmlBlock drops a details/summary scaffold", () => {
    const r = insertHtmlBlock()("", { start: 0, end: 0 });
    expect(r.text).toContain("<details>");
    expect(r.text).toContain("</details>");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/concepts/lib/__tests__/markdownTransforms.test.ts`
Expected: FAIL — "Failed to resolve import ../markdownTransforms".

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/features/concepts/lib/markdownTransforms.ts
export type Sel = { start: number; end: number };
export type TransformResult = { text: string; selection: Sel };
export type Transform = (text: string, sel: Sel) => TransformResult;

function replaceRange(text: string, start: number, end: number, insert: string): string {
  return text.slice(0, start) + insert + text.slice(end);
}

// Wrap/unwrap the selection with the same marker on both sides.
function toggleWrap(marker: string): Transform {
  return (text, sel) => {
    const before = text.slice(sel.start - marker.length, sel.start);
    const after = text.slice(sel.end, sel.end + marker.length);
    if (before === marker && after === marker) {
      // Unwrap: drop the surrounding markers.
      const stripped =
        text.slice(0, sel.start - marker.length) +
        text.slice(sel.start, sel.end) +
        text.slice(sel.end + marker.length);
      return {
        text: stripped,
        selection: { start: sel.start - marker.length, end: sel.end - marker.length },
      };
    }
    const selected = text.slice(sel.start, sel.end);
    const wrapped = `${marker}${selected}${marker}`;
    const next = replaceRange(text, sel.start, sel.end, wrapped);
    if (sel.start === sel.end) {
      // Empty selection: place the cursor between the markers.
      const caret = sel.start + marker.length;
      return { text: next, selection: { start: caret, end: caret } };
    }
    return {
      text: next,
      selection: { start: sel.start + marker.length, end: sel.end + marker.length },
    };
  };
}

// Find the [lineStart, lineEnd) offsets of every line the selection touches.
function lineRange(text: string, sel: Sel): { start: number; end: number } {
  const start = text.lastIndexOf("\n", sel.start - 1) + 1;
  let end = text.indexOf("\n", sel.end);
  if (end === -1) end = text.length;
  return { start, end };
}

// Apply a per-line prefix mutation across the selected lines.
function mapLines(mutate: (line: string, index: number) => string): Transform {
  return (text, sel) => {
    const { start, end } = lineRange(text, sel);
    const block = text.slice(start, end);
    const next = block.split("\n").map(mutate).join("\n");
    const replaced = replaceRange(text, start, end, next);
    return { text: replaced, selection: { start, end: start + next.length } };
  };
}

export const toggleBold = toggleWrap("**");
export const toggleItalic = toggleWrap("*");
export const toggleStrikethrough = toggleWrap("~~");
export const toggleInlineCode = toggleWrap("`");

export function setHeading(level: 1 | 2 | 3): Transform {
  const hashes = "#".repeat(level);
  return mapLines((line) => `${hashes} ${line.replace(/^#{1,6}\s+/, "")}`);
}

export const toggleBulletList: Transform = mapLines((line) =>
  line.startsWith("- ") ? line.slice(2) : `- ${line}`,
);

export const toggleNumberedList: Transform = mapLines((line, i) =>
  /^\d+\.\s/.test(line) ? line.replace(/^\d+\.\s/, "") : `${i + 1}. ${line}`,
);

export const toggleChecklist: Transform = mapLines((line) =>
  line.startsWith("- [ ] ") ? line.slice(6) : `- [ ] ${line}`,
);

export const toggleQuote: Transform = mapLines((line) =>
  line.startsWith("> ") ? line.slice(2) : `> ${line}`,
);

export function insertCodeBlock(lang = ""): Transform {
  return (text, sel) => {
    const selected = text.slice(sel.start, sel.end);
    const block = "```" + lang + "\n" + (selected || "") + "\n```";
    const next = replaceRange(text, sel.start, sel.end, block);
    const caret = sel.start + 3 + lang.length + 1; // start of code line
    return { text: next, selection: { start: caret, end: caret + selected.length } };
  };
}

export function insertTable(rows: number, cols: number): Transform {
  return (text, sel) => {
    const header = "| " + Array.from({ length: cols }, (_, c) => `Column ${c + 1}`).join(" | ") + " |";
    const divider = "| " + Array.from({ length: cols }, () => "---").join(" | ") + " |";
    const bodyRow = "| " + Array.from({ length: cols }, () => "   ").join(" | ") + " |";
    const body = Array.from({ length: rows }, () => bodyRow).join("\n");
    const table = [header, divider, body].join("\n");
    const next = replaceRange(text, sel.start, sel.end, table);
    return { text: next, selection: { start: sel.start, end: sel.start + table.length } };
  };
}

export function insertLink(label: string, href: string): Transform {
  return (text, sel) => {
    const text2 = label || text.slice(sel.start, sel.end) || "link";
    const md = `[${text2}](${href})`;
    const next = replaceRange(text, sel.start, sel.end, md);
    return { text: next, selection: { start: sel.start, end: sel.start + md.length } };
  };
}

export function insertImage(alt: string, src: string): Transform {
  return (text, sel) => {
    const md = `![${alt || "image"}](${src})`;
    const next = replaceRange(text, sel.start, sel.end, md);
    return { text: next, selection: { start: sel.start, end: sel.start + md.length } };
  };
}

export function insertHtmlBlock(): Transform {
  const scaffold = "<details>\n<summary>Details</summary>\n\nContent here.\n\n</details>";
  return (text, sel) => {
    const next = replaceRange(text, sel.start, sel.end, scaffold);
    return { text: next, selection: { start: sel.start, end: sel.start + scaffold.length } };
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/concepts/lib/__tests__/markdownTransforms.test.ts`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/concepts/lib/markdownTransforms.ts frontend/src/features/concepts/lib/__tests__/markdownTransforms.test.ts
git commit -m "feat(editor): pure markdown formatting transforms"
```

---

### Task 2: Mermaid diagram templates

**Files:**
- Create: `frontend/src/features/concepts/lib/mermaidTemplates.ts`
- Test: `frontend/src/features/concepts/lib/__tests__/mermaidTemplates.test.ts`

**Interfaces:**
- Consumes: `Transform` from `markdownTransforms`.
- Produces:
  - `type MermaidKind = "flowchart" | "sequence" | "class" | "state" | "er" | "gantt"`
  - `MERMAID_KINDS: MermaidKind[]`
  - `mermaidSource(kind: MermaidKind): string` (raw diagram body, no fences)
  - `insertMermaid(kind: MermaidKind): Transform` (inserts a fenced ```mermaid block)

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/features/concepts/lib/__tests__/mermaidTemplates.test.ts
import { describe, expect, it } from "vitest";
import { MERMAID_KINDS, mermaidSource, insertMermaid } from "../mermaidTemplates";

describe("mermaidTemplates", () => {
  it("exposes six diagram kinds", () => {
    expect(MERMAID_KINDS).toEqual(["flowchart", "sequence", "class", "state", "er", "gantt"]);
  });

  it("flowchart source starts with a flowchart directive", () => {
    expect(mermaidSource("flowchart")).toContain("flowchart");
  });

  it("insertMermaid wraps the source in a mermaid fence", () => {
    const r = insertMermaid("sequence")("", { start: 0, end: 0 });
    expect(r.text.startsWith("```mermaid\n")).toBe(true);
    expect(r.text.trim().endsWith("```")).toBe(true);
    expect(r.text).toContain("sequenceDiagram");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/concepts/lib/__tests__/mermaidTemplates.test.ts`
Expected: FAIL — cannot resolve `../mermaidTemplates`.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/features/concepts/lib/mermaidTemplates.ts
import type { Transform } from "./markdownTransforms";

export type MermaidKind = "flowchart" | "sequence" | "class" | "state" | "er" | "gantt";

export const MERMAID_KINDS: MermaidKind[] = [
  "flowchart",
  "sequence",
  "class",
  "state",
  "er",
  "gantt",
];

const SOURCES: Record<MermaidKind, string> = {
  flowchart: "flowchart LR\n  A[Start] --> B{Choice}\n  B -->|yes| C[Do this]\n  B -->|no| D[Do that]",
  sequence:
    "sequenceDiagram\n  participant User\n  participant Agent\n  User->>Agent: request\n  Agent-->>User: response",
  class:
    "classDiagram\n  class Skill {\n    +string title\n    +run()\n  }\n  Skill <|-- DataSkill",
  state:
    "stateDiagram-v2\n  [*] --> Draft\n  Draft --> Published\n  Published --> [*]",
  er:
    "erDiagram\n  SKILL ||--o{ VERSION : has\n  SKILL {\n    string title\n  }",
  gantt:
    "gantt\n  title Roadmap\n  dateFormat YYYY-MM-DD\n  section Build\n  Editor :a1, 2026-07-01, 7d",
};

export function mermaidSource(kind: MermaidKind): string {
  return SOURCES[kind];
}

export function insertMermaid(kind: MermaidKind): Transform {
  return (text, sel) => {
    const block = "```mermaid\n" + SOURCES[kind] + "\n```";
    const next = text.slice(0, sel.start) + block + text.slice(sel.end);
    return { text: next, selection: { start: sel.start, end: sel.start + block.length } };
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/concepts/lib/__tests__/mermaidTemplates.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/concepts/lib/mermaidTemplates.ts frontend/src/features/concepts/lib/__tests__/mermaidTemplates.test.ts
git commit -m "feat(editor): mermaid diagram templates"
```

---

### Task 3: Slash-command registry

**Files:**
- Create: `frontend/src/features/concepts/lib/slashCommands.ts`
- Test: `frontend/src/features/concepts/lib/__tests__/slashCommands.test.ts`

**Interfaces:**
- Consumes: transforms from Tasks 1–2.
- Produces:
  - `interface SlashCommand { id: string; label: string; detail: string; keywords: string[]; apply: Transform }`
  - `SLASH_COMMANDS: SlashCommand[]`
  - `filterCommands(query: string): SlashCommand[]`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/features/concepts/lib/__tests__/slashCommands.test.ts
import { describe, expect, it } from "vitest";
import { SLASH_COMMANDS, filterCommands } from "../slashCommands";

describe("slashCommands", () => {
  it("includes table, mermaid, code, and html commands", () => {
    const ids = SLASH_COMMANDS.map((c) => c.id);
    expect(ids).toContain("table");
    expect(ids).toContain("mermaid-flowchart");
    expect(ids).toContain("code");
    expect(ids).toContain("html");
  });

  it("every command has an apply transform that returns text", () => {
    for (const cmd of SLASH_COMMANDS) {
      const r = cmd.apply("", { start: 0, end: 0 });
      expect(typeof r.text).toBe("string");
    }
  });

  it("filterCommands matches on label and keywords, case-insensitively", () => {
    expect(filterCommands("flow").some((c) => c.id === "mermaid-flowchart")).toBe(true);
    expect(filterCommands("TABLE").some((c) => c.id === "table")).toBe(true);
    expect(filterCommands("")).toHaveLength(SLASH_COMMANDS.length);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/concepts/lib/__tests__/slashCommands.test.ts`
Expected: FAIL — cannot resolve `../slashCommands`.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/features/concepts/lib/slashCommands.ts
import {
  insertCodeBlock,
  insertHtmlBlock,
  insertTable,
  setHeading,
  toggleChecklist,
  toggleQuote,
  type Transform,
} from "./markdownTransforms";
import { MERMAID_KINDS, insertMermaid } from "./mermaidTemplates";

export interface SlashCommand {
  id: string;
  label: string;
  detail: string;
  keywords: string[];
  apply: Transform;
}

const SKILL_TEMPLATE: Transform = (text, sel) => {
  const scaffold =
    "# Skill title\n\nOne-sentence summary of what this skill does.\n\n" +
    "## When to use\n\n- ...\n\n## How it works\n\n```mermaid\nflowchart LR\n  A --> B\n```\n";
  return {
    text: text.slice(0, sel.start) + scaffold + text.slice(sel.end),
    selection: { start: sel.start, end: sel.start + scaffold.length },
  };
};

export const SLASH_COMMANDS: SlashCommand[] = [
  { id: "h1", label: "Heading 1", detail: "# Large heading", keywords: ["h1", "title"], apply: setHeading(1) },
  { id: "h2", label: "Heading 2", detail: "## Medium heading", keywords: ["h2"], apply: setHeading(2) },
  { id: "h3", label: "Heading 3", detail: "### Small heading", keywords: ["h3"], apply: setHeading(3) },
  { id: "table", label: "Table", detail: "3×3 GFM table", keywords: ["table", "grid"], apply: insertTable(3, 3) },
  { id: "code", label: "Code block", detail: "Fenced code block", keywords: ["code", "snippet"], apply: insertCodeBlock("") },
  { id: "callout", label: "Callout", detail: "Blockquote callout", keywords: ["callout", "quote", "note"], apply: toggleQuote },
  { id: "checklist", label: "Checklist", detail: "- [ ] task", keywords: ["todo", "task", "check"], apply: toggleChecklist },
  { id: "html", label: "HTML block", detail: "Collapsible <details>", keywords: ["html", "details"], apply: insertHtmlBlock() },
  { id: "skill-template", label: "Skill template", detail: "Starter SKILL.md scaffold", keywords: ["template", "scaffold", "skill"], apply: SKILL_TEMPLATE },
  ...MERMAID_KINDS.map((kind) => ({
    id: `mermaid-${kind}`,
    label: `Mermaid: ${kind}`,
    detail: `Insert a ${kind} diagram`,
    keywords: ["mermaid", "diagram", kind],
    apply: insertMermaid(kind),
  })),
];

export function filterCommands(query: string): SlashCommand[] {
  const q = query.trim().toLowerCase();
  if (!q) return SLASH_COMMANDS;
  return SLASH_COMMANDS.filter(
    (c) => c.label.toLowerCase().includes(q) || c.keywords.some((k) => k.includes(q)),
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/concepts/lib/__tests__/slashCommands.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/concepts/lib/slashCommands.ts frontend/src/features/concepts/lib/__tests__/slashCommands.test.ts
git commit -m "feat(editor): slash-command registry shared by toolbar and slash menu"
```

---

### Task 4: Sanitized HTML in preview

**Files:**
- Create: `frontend/src/features/concepts/lib/sanitizeSchema.ts`
- Modify: `frontend/src/features/concepts/components/MarkdownPreview.tsx`
- Test: `frontend/src/features/concepts/__tests__/MarkdownPreview.test.tsx` (extend existing)

**Interfaces:**
- Consumes: nothing new from earlier tasks.
- Produces: `PREVIEW_SANITIZE_SCHEMA` (hast-util-sanitize schema), `ALLOWED_IFRAME_HOSTS: string[]`, `rehypeIframeAllowlist` (rehype plugin removing iframes with disallowed src hosts).

- [ ] **Step 1: Install dependencies**

Run: `cd frontend && npm install rehype-raw@^7 rehype-sanitize@^6`
Expected: both added to `package.json` dependencies.

- [ ] **Step 2: Write the failing test (extend MarkdownPreview.test.tsx)**

Append these cases inside the existing `describe("MarkdownPreview", ...)` block:

```ts
  it("renders allowed inline HTML (details/summary)", () => {
    render(<MarkdownPreview source={"<details><summary>More</summary>body</details>"} />);
    expect(screen.getByText("More")).toBeInTheDocument();
  });

  it("strips <script> tags from embedded HTML", () => {
    const { container } = render(
      <MarkdownPreview source={"<p>hi</p><script>window.__pwned=1</script>"} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });

  it("drops javascript: links", () => {
    const { container } = render(<MarkdownPreview source={"[x](javascript:alert(1))"} />);
    const a = container.querySelector("a");
    expect(a?.getAttribute("href") ?? "").not.toContain("javascript:");
  });

  it("removes iframes whose src host is not allow-listed", () => {
    const { container } = render(
      <MarkdownPreview source={'<iframe src="https://evil.example/x"></iframe>'} />,
    );
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("keeps iframes from an allow-listed host", () => {
    const { container } = render(
      <MarkdownPreview source={'<iframe src="https://www.youtube.com/embed/abc"></iframe>'} />,
    );
    expect(container.querySelector("iframe")).not.toBeNull();
  });
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/concepts/__tests__/MarkdownPreview.test.tsx`
Expected: FAIL — script/iframe not stripped, details not rendered (raw HTML currently escaped).

- [ ] **Step 4: Write the sanitize schema**

```ts
// frontend/src/features/concepts/lib/sanitizeSchema.ts
import { defaultSchema } from "rehype-sanitize";
import type { Root, Element } from "hast";
import { visit } from "unist-util-visit";

// Hosts whose iframes we allow (embeds). Everything else is dropped.
export const ALLOWED_IFRAME_HOSTS = [
  "www.youtube.com",
  "youtube.com",
  "player.vimeo.com",
];

// Extend the GitHub-safe default with presentational tags + iframe embeds.
export const PREVIEW_SANITIZE_SCHEMA = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "details", "summary", "iframe", "figure", "figcaption"],
  attributes: {
    ...defaultSchema.attributes,
    "*": [...(defaultSchema.attributes?.["*"] ?? []), "className"],
    iframe: ["src", "width", "height", "allow", "allowfullscreen", "title", "frameborder"],
  },
} as typeof defaultSchema;

// Runs AFTER sanitize: drop any iframe whose src host is not allow-listed.
export function rehypeIframeAllowlist() {
  return (tree: Root) => {
    visit(tree, "element", (node: Element, index, parent) => {
      if (node.tagName !== "iframe" || !parent || index === undefined) return;
      const src = String(node.properties?.src ?? "");
      let host = "";
      try {
        host = new URL(src).host;
      } catch {
        host = "";
      }
      if (!ALLOWED_IFRAME_HOSTS.includes(host)) {
        (parent.children as unknown[]).splice(index, 1);
        return [visit.SKIP, index];
      }
    });
  };
}
```

Note: `unist-util-visit` and `hast` types ship transitively with `react-markdown`/`rehype-*`. If `npx tsc --noEmit` reports them missing, run `npm install -D @types/hast unist-util-visit`.

- [ ] **Step 5: Wire the plugins into MarkdownPreview**

Modify `MarkdownPreview.tsx` imports and the `<ReactMarkdown>` call:

```tsx
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { PREVIEW_SANITIZE_SCHEMA, rehypeIframeAllowlist } from "../lib/sanitizeSchema";

// ...inside MarkdownPreview return:
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, PREVIEW_SANITIZE_SCHEMA], rehypeIframeAllowlist]}
        components={{
          code(props) {
            const { className, children } = props as {
              className?: string;
              children?: React.ReactNode;
            };
            const match = /language-(\w+)/.exec(className ?? "");
            if (match?.[1] === "mermaid") {
              return <Mermaid chart={String(children).trim()} />;
            }
            return <code className={className}>{children}</code>;
          },
        }}
      >
        {source}
      </ReactMarkdown>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/concepts/__tests__/MarkdownPreview.test.tsx`
Expected: PASS (all original + 5 new cases). Confirms mermaid + GFM still work and XSS is stripped.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/features/concepts/lib/sanitizeSchema.ts frontend/src/features/concepts/components/MarkdownPreview.tsx frontend/src/features/concepts/__tests__/MarkdownPreview.test.tsx
git commit -m "feat(editor): sanitized raw HTML + iframe allowlist in markdown preview"
```

---

### Task 5: Subtle motion utilities

**Files:**
- Create: `frontend/src/features/shared/fancy/NumberTicker.tsx`
- Create: `frontend/src/features/shared/fancy/SaveFlash.tsx`
- Test: `frontend/src/features/shared/fancy/__tests__/NumberTicker.test.tsx`

**Interfaces:**
- Produces:
  - `NumberTicker({ value, className?, style? })` — animates from previous to new value; renders the current integer as text.
  - `SaveFlash({ show })` — a small check-mark badge that fades; renders "Saved" text when `show` is true.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/shared/fancy/__tests__/NumberTicker.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NumberTicker } from "../NumberTicker";

describe("NumberTicker", () => {
  it("renders the target value as text", () => {
    render(<NumberTicker value={42} />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/NumberTicker.test.tsx`
Expected: FAIL — cannot resolve `../NumberTicker`.

- [ ] **Step 3: Write minimal implementations**

```tsx
// frontend/src/features/shared/fancy/NumberTicker.tsx
import { useEffect, useRef, useState } from "react";

/** Animates a number toward `value` via requestAnimationFrame. */
export function NumberTicker({
  value,
  className,
  style,
}: {
  value: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);

  useEffect(() => {
    const from = fromRef.current;
    const to = value;
    if (from === to) return;
    const start = performance.now();
    const dur = 400;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return (
    <span className={className} style={style}>
      {display}
    </span>
  );
}

export default NumberTicker;
```

```tsx
// frontend/src/features/shared/fancy/SaveFlash.tsx
import { CheckCircleFilled } from "@ant-design/icons";
import { tokens } from "@/app/theme/tokens";

/** Brief "Saved" confirmation badge; parent controls visibility timing. */
export function SaveFlash({ show }: { show: boolean }) {
  return (
    <span
      role="status"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        color: tokens.color.ok,
        fontSize: 13,
        opacity: show ? 1 : 0,
        transform: show ? "translateY(0)" : "translateY(4px)",
        transition: "opacity 240ms ease, transform 240ms ease",
        pointerEvents: "none",
      }}
    >
      {show && (
        <>
          <CheckCircleFilled /> Saved
        </>
      )}
    </span>
  );
}

export default SaveFlash;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/shared/fancy/__tests__/NumberTicker.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/shared/fancy/
git commit -m "feat(editor): subtle motion utils (number ticker, save flash)"
```

---

### Task 6: Monaco editor wrapper

**Files:**
- Create: `frontend/src/features/concepts/components/editor/SkillEditor.tsx`
- Modify: `frontend/vite.config.ts` (manualChunks for monaco)
- Test: `frontend/src/features/concepts/components/editor/__tests__/SkillEditor.test.tsx`

**Interfaces:**
- Consumes: `SLASH_COMMANDS`, `filterCommands` (Task 3), `Transform`/`Sel` (Task 1).
- Produces:
  - `interface SkillEditorHandle { applyTransform(t: Transform): void }`
  - `SkillEditor` = `forwardRef<SkillEditorHandle, { value: string; onChange: (v: string) => void }>` — lazy-loads Monaco, registers the slash completion provider, exposes `applyTransform`.

- [ ] **Step 1: Install dependencies**

Run: `cd frontend && npm install @monaco-editor/react@^4 monaco-editor@^0.52`
Expected: both added to dependencies.

- [ ] **Step 2: Configure the Monaco chunk in vite.config.ts**

Add a `build.rollupOptions.output.manualChunks` entry so Monaco is a separate chunk:

```ts
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ["monaco-editor", "@monaco-editor/react"],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
```

- [ ] **Step 3: Write the failing test (Monaco mocked)**

```tsx
// frontend/src/features/concepts/components/editor/__tests__/SkillEditor.test.tsx
import { render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { SkillEditor, type SkillEditorHandle } from "../SkillEditor";
import { toggleBold } from "@/features/concepts/lib/markdownTransforms";

// Monaco does not run in jsdom — replace it with a controlled <textarea>.
vi.mock("@monaco-editor/react", () => ({
  default: ({ value, onChange }: { value: string; onChange: (v?: string) => void }) => (
    <textarea aria-label="monaco" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

describe("SkillEditor", () => {
  it("renders the (mocked) editor with the given value", () => {
    render(<SkillEditor value={"hello"} onChange={() => {}} />);
    expect(screen.getByLabelText("monaco")).toHaveValue("hello");
  });

  it("applyTransform runs a transform against the current value and emits onChange", () => {
    const onChange = vi.fn();
    const ref = createRef<SkillEditorHandle>();
    render(<SkillEditor ref={ref} value={"word"} onChange={onChange} />);
    ref.current!.applyTransform(toggleBold);
    // With no live Monaco selection the fallback selects the whole document.
    expect(onChange).toHaveBeenCalledWith("**word**");
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/concepts/components/editor/__tests__/SkillEditor.test.tsx`
Expected: FAIL — cannot resolve `../SkillEditor`.

- [ ] **Step 5: Write the implementation**

```tsx
// frontend/src/features/concepts/components/editor/SkillEditor.tsx
import Editor, { type OnMount } from "@monaco-editor/react";
import { forwardRef, useImperativeHandle, useRef } from "react";
import { tokens } from "@/app/theme/tokens";
import type { Sel, Transform } from "@/features/concepts/lib/markdownTransforms";
import { filterCommands } from "@/features/concepts/lib/slashCommands";

export interface SkillEditorHandle {
  applyTransform(t: Transform): void;
}

type MonacoEditor = Parameters<OnMount>[0];
type Monaco = Parameters<OnMount>[1];

export const SkillEditor = forwardRef<SkillEditorHandle, {
  value: string;
  onChange: (v: string) => void;
}>(function SkillEditor({ value, onChange }, ref) {
  const editorRef = useRef<MonacoEditor | null>(null);

  function offsetsFromEditor(ed: MonacoEditor): Sel {
    const model = ed.getModel();
    const selection = ed.getSelection();
    if (!model || !selection) return { start: 0, end: value.length };
    return {
      start: model.getOffsetAt({ lineNumber: selection.startLineNumber, column: selection.startColumn }),
      end: model.getOffsetAt({ lineNumber: selection.endLineNumber, column: selection.endColumn }),
    };
  }

  useImperativeHandle(ref, () => ({
    applyTransform(t: Transform) {
      const ed = editorRef.current;
      // Fallback when Monaco is not mounted (tests / first paint): whole-doc selection.
      const sel: Sel = ed ? offsetsFromEditor(ed) : { start: 0, end: value.length };
      const result = t(value, sel);
      onChange(result.text);
      if (ed) {
        const model = ed.getModel();
        if (model) {
          const startPos = model.getPositionAt(result.selection.start);
          const endPos = model.getPositionAt(result.selection.end);
          ed.setSelection({
            startLineNumber: startPos.lineNumber,
            startColumn: startPos.column,
            endLineNumber: endPos.lineNumber,
            endColumn: endPos.column,
          });
          ed.focus();
        }
      }
    },
  }));

  const handleMount: OnMount = (editor, monaco: Monaco) => {
    editorRef.current = editor;
    registerSlash(monaco);
  };

  return (
    <Editor
      height="100%"
      defaultLanguage="markdown"
      value={value}
      onChange={(v) => onChange(v ?? "")}
      onMount={handleMount}
      options={{
        wordWrap: "on",
        minimap: { enabled: false },
        fontFamily: tokens.font.mono,
        fontSize: 13,
        lineNumbers: "off",
        scrollBeyondLastLine: false,
        padding: { top: 12 },
      }}
    />
  );
});

// Register the `/` slash menu as a Monaco completion provider (idempotent).
let slashRegistered = false;
function registerSlash(monaco: Monaco) {
  if (slashRegistered) return;
  slashRegistered = true;
  monaco.languages.registerCompletionItemProvider("markdown", {
    triggerCharacters: ["/"],
    provideCompletionItems(model, position) {
      const line = model.getLineContent(position.lineNumber).slice(0, position.column - 1);
      const match = /\/(\w*)$/.exec(line);
      if (!match) return { suggestions: [] };
      const query = match[1];
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn - 1, // include the leading "/"
        endColumn: word.endColumn,
      };
      const suggestions = filterCommands(query).map((cmd) => {
        const applied = cmd.apply("", { start: 0, end: 0 });
        return {
          label: `/${cmd.id}`,
          kind: monaco.languages.CompletionItemKind.Snippet,
          detail: cmd.detail,
          documentation: cmd.label,
          insertText: applied.text,
          range,
        };
      });
      return { suggestions };
    },
  });
}

export default SkillEditor;
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/concepts/components/editor/__tests__/SkillEditor.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/features/concepts/components/editor/SkillEditor.tsx frontend/src/features/concepts/components/editor/__tests__/SkillEditor.test.tsx
git commit -m "feat(editor): Monaco markdown editor wrapper with slash completion"
```

---

### Task 7: Editor toolbar

**Files:**
- Create: `frontend/src/features/concepts/components/editor/EditorToolbar.tsx`
- Test: `frontend/src/features/concepts/components/editor/__tests__/EditorToolbar.test.tsx`

**Interfaces:**
- Consumes: transforms (Task 1), mermaid `MERMAID_KINDS`/`insertMermaid` (Task 2), `Transform` type.
- Produces: `EditorToolbar({ onApply, onInsertConceptLink })` where `onApply: (t: Transform) => void` and `onInsertConceptLink: () => void` (opens the existing concept-link modal owned by the page).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/concepts/components/editor/__tests__/EditorToolbar.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EditorToolbar } from "../EditorToolbar";
import type { Transform } from "@/features/concepts/lib/markdownTransforms";

describe("EditorToolbar", () => {
  it("applies bold when the Bold button is clicked", async () => {
    const onApply = vi.fn();
    render(<EditorToolbar onApply={onApply} onInsertConceptLink={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /bold/i }));
    const t = onApply.mock.calls[0][0] as Transform;
    expect(t("word", { start: 0, end: 4 }).text).toBe("**word**");
  });

  it("opens the concept-link modal via its callback", async () => {
    const onLink = vi.fn();
    render(<EditorToolbar onApply={() => {}} onInsertConceptLink={onLink} />);
    await userEvent.click(screen.getByRole("button", { name: /link concept/i }));
    expect(onLink).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/concepts/components/editor/__tests__/EditorToolbar.test.tsx`
Expected: FAIL — cannot resolve `../EditorToolbar`.

- [ ] **Step 3: Write the implementation**

```tsx
// frontend/src/features/concepts/components/editor/EditorToolbar.tsx
import {
  BoldOutlined,
  ItalicOutlined,
  StrikethroughOutlined,
  CodeOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  CheckSquareOutlined,
  LinkOutlined,
  TableOutlined,
  PictureOutlined,
  Html5Outlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import { Button, Dropdown, Space, Tooltip } from "antd";
import { tokens } from "@/app/theme/tokens";
import {
  insertCodeBlock,
  insertHtmlBlock,
  insertImage,
  insertTable,
  setHeading,
  toggleBold,
  toggleBulletList,
  toggleChecklist,
  toggleInlineCode,
  toggleItalic,
  toggleNumberedList,
  toggleQuote,
  toggleStrikethrough,
  type Transform,
} from "@/features/concepts/lib/markdownTransforms";
import { MERMAID_KINDS, insertMermaid } from "@/features/concepts/lib/mermaidTemplates";

export function EditorToolbar({
  onApply,
  onInsertConceptLink,
}: {
  onApply: (t: Transform) => void;
  onInsertConceptLink: () => void;
}) {
  const btn = (label: string, icon: React.ReactNode, t: Transform) => (
    <Tooltip title={label} key={label}>
      <Button size="small" type="text" aria-label={label} icon={icon} onClick={() => onApply(t)} />
    </Tooltip>
  );

  const headingItems = [1, 2, 3].map((lvl) => ({
    key: `h${lvl}`,
    label: `Heading ${lvl}`,
    onClick: () => onApply(setHeading(lvl as 1 | 2 | 3)),
  }));

  const mermaidItems = MERMAID_KINDS.map((k) => ({
    key: k,
    label: `Mermaid: ${k}`,
    onClick: () => onApply(insertMermaid(k)),
  }));

  return (
    <Space
      wrap
      size={2}
      style={{
        padding: "6px 8px",
        borderBottom: `1px solid ${tokens.color.line}`,
        background: tokens.color.surface,
      }}
    >
      {btn("Bold", <BoldOutlined />, toggleBold)}
      {btn("Italic", <ItalicOutlined />, toggleItalic)}
      {btn("Strikethrough", <StrikethroughOutlined />, toggleStrikethrough)}
      {btn("Inline code", <CodeOutlined />, toggleInlineCode)}
      <Dropdown menu={{ items: headingItems }} trigger={["click"]}>
        <Button size="small" type="text" aria-label="Heading">H</Button>
      </Dropdown>
      {btn("Bullet list", <UnorderedListOutlined />, toggleBulletList)}
      {btn("Numbered list", <OrderedListOutlined />, toggleNumberedList)}
      {btn("Checklist", <CheckSquareOutlined />, toggleChecklist)}
      {btn("Quote", <span style={{ fontFamily: tokens.font.mono }}>&gt;</span>, toggleQuote)}
      {btn("Code block", <CodeOutlined />, insertCodeBlock(""))}
      {btn("Table", <TableOutlined />, insertTable(3, 3))}
      <Dropdown menu={{ items: mermaidItems }} trigger={["click"]}>
        <Tooltip title="Mermaid diagram">
          <Button size="small" type="text" aria-label="Mermaid" icon={<NodeIndexOutlined />} />
        </Tooltip>
      </Dropdown>
      {btn("Image", <PictureOutlined />, insertImage("image", "https://"))}
      {btn("HTML block", <Html5Outlined />, insertHtmlBlock())}
      <Tooltip title="Link a concept (graph edge)">
        <Button
          size="small"
          type="text"
          aria-label="Link concept"
          icon={<LinkOutlined />}
          onClick={onInsertConceptLink}
        />
      </Tooltip>
    </Space>
  );
}

export default EditorToolbar;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/concepts/components/editor/__tests__/EditorToolbar.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/concepts/components/editor/EditorToolbar.tsx frontend/src/features/concepts/components/editor/__tests__/EditorToolbar.test.tsx
git commit -m "feat(editor): formatting toolbar wired to pure transforms"
```

---

### Task 8: Compose into ConceptEditorPage

**Files:**
- Modify: `frontend/src/features/concepts/pages/ConceptEditorPage.tsx` (replace the `editorTab` block; add view-mode state, ref, lazy Suspense, SaveFlash)
- Modify: `frontend/src/features/concepts/__tests__/ConceptEditor.test.tsx` (keep passing; Monaco mocked)

**Interfaces:**
- Consumes: `SkillEditor` + `SkillEditorHandle` (Task 6), `EditorToolbar` (Task 7), `NumberTicker` + `SaveFlash` (Task 5). The existing concept-link modal (`linkOpen`, `insertLink`) is reused for `onInsertConceptLink`.

- [ ] **Step 1: Inspect the current test to preserve its expectations**

Run: `cd frontend && sed -n '1,80p' src/features/concepts/__tests__/ConceptEditor.test.tsx`
Note which labels/roles it asserts. The change must keep those working; Monaco is mocked the same way as Task 6. If the existing test targeted the raw `<textarea>` by `aria-label="Concept body"`, update that query to the mocked `aria-label="monaco"` textarea (the Monaco mock in Step 2), since the raw textarea is being replaced.

- [ ] **Step 2: Add the Monaco mock to the existing test file (if not present)**

At the top of `ConceptEditor.test.tsx`, add the same mock used in Task 6 so the page renders in jsdom:

```tsx
vi.mock("@monaco-editor/react", () => ({
  default: ({ value, onChange }: { value: string; onChange: (v?: string) => void }) => (
    <textarea aria-label="monaco" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));
```

- [ ] **Step 3: Replace the editorTab in ConceptEditorPage.tsx**

Add imports near the other feature imports (note: `Segmented` joins the existing antd import; `useRef`/`useState` are already imported — do not duplicate):

```tsx
import { Segmented } from "antd";
import { Suspense, lazy } from "react";
import type { SkillEditorHandle } from "../components/editor/SkillEditor";
import { EditorToolbar } from "../components/editor/EditorToolbar";
import type { Transform } from "../lib/markdownTransforms";
import { NumberTicker } from "@/features/shared/fancy/NumberTicker";
import { SaveFlash } from "@/features/shared/fancy/SaveFlash";

const SkillEditor = lazy(() =>
  import("../components/editor/SkillEditor").then((m) => ({ default: m.SkillEditor })),
);
```

Add state/handlers inside the component (near the other `useState`s):

```tsx
  const [mode, setMode] = useState<"edit" | "split" | "preview">("split");
  const [saved, setSaved] = useState(false);
  const editorRef = useRef<SkillEditorHandle>(null);

  const applyTransform = (t: Transform) => editorRef.current?.applyTransform(t);
  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;
```

Update `save()` to flash confirmation:

```tsx
  async function save() {
    const v = await form.validateFields();
    await update.mutateAsync({ ...v, body });
    message.success("Saved");
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
  }
```

Replace the whole `editorTab` constant with:

```tsx
  const showEditor = mode !== "preview";
  const showPreview = mode !== "edit";
  const editorTab = (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Segmented
          size="small"
          value={mode}
          onChange={(v) => setMode(v as typeof mode)}
          options={[
            { label: "Edit", value: "edit" },
            { label: "Split", value: "split" },
            { label: "Preview", value: "preview" },
          ]}
        />
        <Space size={16}>
          <SaveFlash show={saved} />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            <NumberTicker value={wordCount} /> words
          </Typography.Text>
        </Space>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: mode === "split" ? "1fr 1fr" : "1fr",
          gap: 20,
          minHeight: 460,
        }}
      >
        {showEditor && (
          <div
            style={{
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              minHeight: 460,
            }}
          >
            <EditorToolbar onApply={applyTransform} onInsertConceptLink={() => setLinkOpen(true)} />
            <div style={{ flex: 1, minHeight: 400 }}>
              <Suspense fallback={<Spin style={{ margin: 40 }} />}>
                <SkillEditor ref={editorRef} value={body} onChange={setBody} />
              </Suspense>
            </div>
          </div>
        )}
        {showPreview && (
          <div
            style={{
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              padding: 16,
              background: tokens.color.surface,
              overflow: "auto",
            }}
          >
            <MarkdownPreview source={body} />
          </div>
        )}
      </div>
    </div>
  );
```

The existing `insertLink` function and concept-link `Modal` are unchanged — the toolbar's "Link concept" button now opens that same modal via `setLinkOpen(true)`. The old `cursorRef`-based `insertLink` appends at document end when no Monaco cursor is tracked; that behavior is acceptable and unchanged. The old inline `<Input.TextArea aria-label="Concept body">` and its `onSelect`/`cursorRef` wiring are removed as part of replacing `editorTab`.

- [ ] **Step 4: Run the page test + typecheck**

Run: `cd frontend && npx vitest run src/features/concepts/__tests__/ConceptEditor.test.tsx && npx tsc --noEmit`
Expected: PASS + no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/concepts/pages/ConceptEditorPage.tsx frontend/src/features/concepts/__tests__/ConceptEditor.test.tsx
git commit -m "feat(editor): compose Monaco editor, toolbar, view modes into concept editor"
```

---

### Task 9: Full verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full test suite**

Run: `cd frontend && npm test -- run`
Expected: all suites pass (new + pre-existing).

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Lint (if configured)**

Run: `cd frontend && npm run lint`
Expected: no new errors. (If the script is absent, skip.)

- [ ] **Step 4: Production build (confirms Monaco chunk + no bundle break)**

Run: `cd frontend && npm run build`
Expected: build succeeds; output shows a separate `monaco` chunk.

- [ ] **Step 5: Manual smoke (optional, if a dev server is run)**

Open a concept in the editor. Verify: toolbar Bold/Table/Mermaid insert correct markdown; `/` shows the slash menu; Split/Edit/Preview toggle works; a mermaid block renders in preview; an embedded `<details>` renders while a `<script>` does not; Save shows the "Saved" flash.

- [ ] **Step 6: Final commit (if any lint/format fixups were needed)**

```bash
git add -A
git commit -m "chore(editor): verification fixups" || echo "nothing to commit"
```

---

## Self-Review

**1. Spec coverage:**
- §2 Monaco surface → Task 6. Toolbar → Task 7. Slash menu → Tasks 3 + 6. ✓
- §3 pure transforms (`markdownTransforms`, `mermaidTemplates`, `slashCommands`) → Tasks 1–3. ✓
- §5 feature set (bold/italic/strike/headings/lists/quote/code/table/mermaid/image/html/concept-link) → Tasks 1, 2, 7. ✓
- §6 sanitized HTML (`rehype-raw` + `rehype-sanitize` + iframe allowlist) → Task 4. ✓
- §7 view modes + subtle motion → Tasks 5 + 8. ✓
- §8 testing (pure unit tests, sanitize XSS, Monaco mocked) → every task + Task 9. ✓
- §9 dependencies → installed in Tasks 4 and 6. ✓
- §10 risks (lazy-load, mock Monaco, sanitize allowlist, shared slash registry) → Tasks 3, 4, 6. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows full code; every test shows real assertions. ✓

**3. Type consistency:** `Sel`, `TransformResult`, `Transform` defined in Task 1 and reused verbatim in Tasks 2, 3, 6, 7, 8. `SkillEditorHandle.applyTransform(t: Transform)` defined in Task 6, consumed in Task 8. `SlashCommand` defined in Task 3, consumed in Task 6. `mermaidSource`/`insertMermaid`/`MERMAID_KINDS` defined in Task 2, consumed in Tasks 3, 7. ✓

No gaps found.
