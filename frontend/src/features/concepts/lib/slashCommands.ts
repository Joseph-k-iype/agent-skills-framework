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
