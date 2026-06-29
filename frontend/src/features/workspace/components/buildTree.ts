import type { DataNode } from "antd/es/tree";
import type { Folder } from "../api/workspaceApi";

/** A concept file to place in the tree under its directory. */
export interface ConceptNode {
  path: string; // repo-relative, e.g. "finance/payments/invoice-ocr.md"
  title: string;
  type?: string;
}

const FILE_PREFIX = "file:";

/** A tree key encodes whether the node is a folder (id) or a file ("file:<path>"). */
export function fileKey(path: string): string {
  return FILE_PREFIX + path;
}
export function isFileKey(key: string): boolean {
  return key.startsWith(FILE_PREFIX);
}
export function pathFromKey(key: string): string {
  return key.slice(FILE_PREFIX.length);
}

function dirOf(path: string): string {
  const i = path.lastIndexOf("/");
  return i === -1 ? "" : path.slice(0, i);
}

function normFolderPath(folder: Folder): string {
  return (folder.path ?? "").replace(/^\//, "");
}

/**
 * Convert a flat folder list (each with parent_id) plus concept files into Ant
 * Tree nodes. Files are nested under the folder whose path matches their
 * directory; root-level files appear at the top.
 */
export function buildTree(
  folders: Folder[],
  concepts: ConceptNode[],
  workspaceId: string,
): DataNode[] {
  const byParent = new Map<string, Folder[]>();
  for (const f of folders) {
    const key = f.parent_id ?? workspaceId;
    const arr = byParent.get(key) ?? [];
    arr.push(f);
    byParent.set(key, arr);
  }

  const filesByDir = new Map<string, ConceptNode[]>();
  for (const c of concepts) {
    const dir = dirOf(c.path);
    const arr = filesByDir.get(dir) ?? [];
    arr.push(c);
    filesByDir.set(dir, arr);
  }

  const fileNodes = (dir: string): DataNode[] =>
    (filesByDir.get(dir) ?? [])
      .sort((a, b) => a.title.localeCompare(b.title))
      .map((c) => ({ key: fileKey(c.path), title: c.title, isLeaf: true }));

  const build = (parentId: string, parentDir: string): DataNode[] => {
    const folderNodes = (byParent.get(parentId) ?? [])
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((f) => ({
        key: f.id,
        title: f.name,
        children: build(f.id, normFolderPath(f)),
      }));
    return [...folderNodes, ...fileNodes(parentDir)];
  };

  return build(workspaceId, "");
}
