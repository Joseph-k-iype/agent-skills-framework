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
