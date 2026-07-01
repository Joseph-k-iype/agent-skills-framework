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
