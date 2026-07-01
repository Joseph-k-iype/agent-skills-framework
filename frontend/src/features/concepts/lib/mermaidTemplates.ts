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
