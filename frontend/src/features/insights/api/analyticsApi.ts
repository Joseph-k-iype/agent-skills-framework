import { useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface EvalKindSummary {
  kind: string;
  runs: number;
  avg_score: number | null;
}
export interface EvalPerConcept {
  concept_path: string;
  kind: string;
  runs: number;
  avg_score: number | null;
}
export interface EvalRecent {
  workspace_id: string;
  concept_path: string;
  kind: string;
  score: number | null;
  summary: string | null;
  created_at: string | null;
}
export interface MostInstalled {
  title: string;
  version: string;
  downloads: number;
  type?: string | null;
}
export interface GraphAnalytics {
  concepts: number;
  references: number;
  types: { type: string; count: number }[];
  hubs: { path: string; title: string; degree: number }[];
  orphans: { path: string; title: string }[];
}
export interface AnalyticsOverview {
  eval_summary: EvalKindSummary[];
  eval_per_concept: EvalPerConcept[];
  eval_recent: EvalRecent[];
  most_installed: MostInstalled[];
  graph: GraphAnalytics | null;
}

export function useAnalyticsOverview(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ["analytics-overview", workspaceId ?? ""],
    queryFn: () =>
      unwrap<AnalyticsOverview>(
        http.get(`/analytics/overview`, {
          params: { workspace_id: workspaceId || undefined },
        }),
      ),
  });
}
