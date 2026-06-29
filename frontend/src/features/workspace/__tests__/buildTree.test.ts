import { describe, expect, it } from "vitest";
import { buildTree, fileKey, isFileKey, pathFromKey, type ConceptNode } from "../components/buildTree";
import type { Folder } from "../api/workspaceApi";

const f = (id: string, name: string, parent_id: string | null, path: string | null = null): Folder => ({
  id,
  name,
  parent_id,
  workspace_id: "w1",
  status: "active",
  path,
});

describe("buildTree", () => {
  it("nests folders by parent and sorts siblings by name", () => {
    const folders = [
      f("f1", "Reports", "w1"),
      f("f2", "Quarterly", "f1"),
      f("f3", "Audits", "w1"),
    ];
    const tree = buildTree(folders, [], "w1");
    expect(tree.map((n) => n.title)).toEqual(["Audits", "Reports"]); // sorted
    const reports = tree.find((n) => n.title === "Reports");
    expect(reports?.children?.[0].title).toBe("Quarterly");
  });

  it("treats folders whose parent is the workspace as top-level", () => {
    const tree = buildTree([f("f1", "A", "w1")], [], "w1");
    expect(tree).toHaveLength(1);
    expect(tree[0].key).toBe("f1");
  });

  it("returns an empty array when there are no folders or files", () => {
    expect(buildTree([], [], "w1")).toEqual([]);
  });

  it("nests concept files under the folder matching their directory", () => {
    const folders = [f("f1", "Payments", "w1", "/payments")];
    const concepts: ConceptNode[] = [
      { path: "payments/invoice-ocr.md", title: "Invoice OCR" },
      { path: "readme.md", title: "Readme" },
    ];
    const tree = buildTree(folders, concepts, "w1");
    // root-level file appears at top alongside folders
    expect(tree.some((n) => n.key === fileKey("readme.md"))).toBe(true);
    const payments = tree.find((n) => n.title === "Payments");
    expect(payments?.children?.[0].key).toBe(fileKey("payments/invoice-ocr.md"));
    expect((payments?.children?.[0] as { isLeaf?: boolean }).isLeaf).toBe(true);
  });

  it("file key helpers round-trip", () => {
    const k = fileKey("a/b.md");
    expect(isFileKey(k)).toBe(true);
    expect(pathFromKey(k)).toBe("a/b.md");
  });
});
