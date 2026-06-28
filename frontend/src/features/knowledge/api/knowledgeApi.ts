import { useMutation, useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface SearchResult {
  id: string;
  title: string;
  type: string;
  relative_path: string;
  score: number;
  provenance: {
    source_repository?: string;
    references: { id: string; title: string }[];
    folder_id?: string | null;
  };
}

export interface SearchResponse {
  query: string;
  semantic: boolean;
  results: SearchResult[];
}

export interface GraphEdge {
  rel: string;
  dir: "in" | "out";
  id: string;
  label: string;
  kind: string;
}

export interface Neighborhood {
  node: { id: string; title?: string; name?: string; type?: string };
  edges: GraphEdge[];
}

export interface ImportResult {
  documents: number;
  references: number;
  embedded: number;
  orphans: string[];
  document_ids: string[];
}

export function useSearch(query: string, enabled: boolean) {
  return useQuery({
    queryKey: ["knowledge-search", query],
    queryFn: () => unwrap<SearchResponse>(http.get("/knowledge/search", { params: { q: query, k: 10 } })),
    enabled: enabled && query.trim().length > 0,
  });
}

export function useNeighborhood(nodeId: string | null) {
  return useQuery({
    queryKey: ["knowledge-graph", nodeId],
    queryFn: () => unwrap<Neighborhood>(http.get(`/knowledge/graph/${nodeId}`)),
    enabled: !!nodeId,
  });
}

export interface OkfDocSummary {
  id: string;
  title: string;
  type: string;
  relative_path?: string;
}

export function useDocuments(workspaceId?: string) {
  return useQuery({
    queryKey: ["knowledge-docs", workspaceId ?? "all"],
    queryFn: () =>
      unwrap<OkfDocSummary[]>(
        http.get("/knowledge/documents", { params: workspaceId ? { workspace_id: workspaceId } : {} }),
      ),
  });
}

export function useImportOkf() {
  return useMutation({
    mutationFn: (body: { source_repository: string; workspace_id?: string; folder_id?: string }) =>
      unwrap<ImportResult>(http.post("/knowledge/okf/import", body)),
  });
}
