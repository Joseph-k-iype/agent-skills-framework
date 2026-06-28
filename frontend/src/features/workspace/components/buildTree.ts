import type { DataNode } from "antd/es/tree";
import type { Folder } from "../api/workspaceApi";

/** Convert a flat folder list (each with parent_id) into Ant Tree nodes. */
export function buildTree(folders: Folder[], workspaceId: string): DataNode[] {
  const byParent = new Map<string, Folder[]>();
  for (const f of folders) {
    const key = f.parent_id ?? workspaceId;
    const arr = byParent.get(key) ?? [];
    arr.push(f);
    byParent.set(key, arr);
  }
  const build = (parentId: string): DataNode[] =>
    (byParent.get(parentId) ?? [])
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((f) => ({
        key: f.id,
        title: f.name,
        children: build(f.id),
      }));
  return build(workspaceId);
}
