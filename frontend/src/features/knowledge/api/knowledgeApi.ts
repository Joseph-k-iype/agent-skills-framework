import { useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface SearchHit {
  path: string;
  title: string;
  type: string;
  runtime?: string | null;
  description?: string | null;
  score: number;
}

// Shape consumed by GraphRelationshipView.
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

export function useWorkspaceSearch(
  workspaceId: string | undefined,
  query: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["ws-search", workspaceId ?? "", query],
    queryFn: () =>
      unwrap<SearchHit[]>(http.get(`/workspaces/${workspaceId}/search`, { params: { q: query } })),
    enabled: enabled && !!workspaceId && query.trim().length > 0,
  });
}

interface RawNeighbor {
  dir: "in" | "out";
  path: string;
  title?: string;
  type?: string;
}
interface RawNeighborhood {
  node: { path: string; title?: string; type?: string } | null;
  edges: RawNeighbor[];
}

export function useConceptNeighborhood(workspaceId: string | undefined, path: string | null) {
  return useQuery({
    queryKey: ["ws-graph", workspaceId ?? "", path],
    queryFn: async (): Promise<Neighborhood | undefined> => {
      const raw = await unwrap<RawNeighborhood>(
        http.get(`/workspaces/${workspaceId}/concept/graph`, { params: { path } }),
      );
      if (!raw.node) return undefined;
      return {
        node: { id: raw.node.path, title: raw.node.title, type: raw.node.type },
        edges: (raw.edges ?? []).map((e) => ({
          rel: "references",
          dir: e.dir,
          id: e.path,
          label: e.title ?? e.path,
          kind: e.type ?? "Concept",
        })),
      };
    },
    enabled: !!workspaceId && !!path,
  });
}
