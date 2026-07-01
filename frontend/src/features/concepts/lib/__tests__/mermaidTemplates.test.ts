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
