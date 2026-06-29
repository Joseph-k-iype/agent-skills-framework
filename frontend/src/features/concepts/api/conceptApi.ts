import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface ConceptRef {
  path: string;
  title?: string | null;
  type?: string | null;
}

export interface Concept {
  workspace_id: string;
  path: string;
  type: string;
  title: string;
  description?: string | null;
  runtime?: string | null;
  tags: string[];
  capabilities: string[];
  body: string;
  frontmatter: Record<string, unknown>;
  links: string[];
  references: ConceptRef[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ConceptSummary {
  workspace_id: string;
  path: string;
  type: string;
  title: string;
  description?: string | null;
  runtime?: string | null;
  tags: string[];
}

export interface VersionEntry {
  sha: string;
  message: string;
  author: string;
  ts: string;
}

export interface EvalFinding {
  severity: string;
  message: string;
  evidence?: string | null;
}

export interface EvalResult {
  evaluator: string;
  score: number;
  findings: EvalFinding[];
  blocking: boolean;
  used_llm: boolean;
}

export interface EvalReport {
  overall_score: number;
  confidence: number;
  passed: boolean;
  results: EvalResult[];
  blocking_issues: string[];
  recommendations: string[];
  used_llm: boolean;
}

export interface SearchHit {
  path: string;
  title: string;
  type: string;
  runtime?: string | null;
  description?: string | null;
  score: number;
}

const keys = {
  list: (ws: string) => ["concepts", ws] as const,
  one: (ws: string, path: string) => ["concept", ws, path] as const,
  history: (ws: string, path: string) => ["concept-history", ws, path] as const,
};

export function useConcepts(workspaceId: string | undefined) {
  return useQuery({
    queryKey: keys.list(workspaceId ?? ""),
    queryFn: () => unwrap<ConceptSummary[]>(http.get(`/workspaces/${workspaceId}/concepts`)),
    enabled: !!workspaceId,
  });
}

export function useConcept(workspaceId: string | undefined, path: string | undefined) {
  return useQuery({
    queryKey: keys.one(workspaceId ?? "", path ?? ""),
    queryFn: () =>
      unwrap<Concept>(http.get(`/workspaces/${workspaceId}/concept`, { params: { path } })),
    enabled: !!workspaceId && !!path,
  });
}

export function useConceptHistory(workspaceId: string | undefined, path: string | undefined) {
  return useQuery({
    queryKey: keys.history(workspaceId ?? "", path ?? ""),
    queryFn: () =>
      unwrap<VersionEntry[]>(
        http.get(`/workspaces/${workspaceId}/concept/history`, { params: { path } }),
      ),
    enabled: !!workspaceId && !!path,
  });
}

export interface CreateConceptBody {
  name: string;
  folder_path?: string;
  type?: string;
  description?: string | null;
  runtime?: string | null;
  tags?: string[];
  capabilities?: string[];
  body?: string;
  frontmatter?: Record<string, unknown>;
}

export function useCreateConcept(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateConceptBody) =>
      unwrap<Concept>(http.post(`/workspaces/${workspaceId}/concepts`, body)),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(workspaceId) }),
  });
}

export interface UpdateConceptBody {
  title?: string | null;
  type?: string | null;
  description?: string | null;
  runtime?: string | null;
  tags?: string[];
  capabilities?: string[];
  body?: string;
  frontmatter?: Record<string, unknown>;
}

export function useUpdateConcept(workspaceId: string, path: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateConceptBody) =>
      unwrap<Concept>(http.put(`/workspaces/${workspaceId}/concept`, body, { params: { path } })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.one(workspaceId, path) });
      qc.invalidateQueries({ queryKey: keys.list(workspaceId) });
    },
  });
}

export function useDeleteConcept(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) =>
      unwrap(http.delete(`/workspaces/${workspaceId}/concept`, { params: { path } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list(workspaceId) }),
  });
}

export function useEvaluateConcept(workspaceId: string, path: string) {
  return useMutation({
    mutationFn: () =>
      unwrap<EvalReport>(http.post(`/workspaces/${workspaceId}/concept/evaluate`, null, { params: { path } })),
  });
}

export interface DeepCase {
  scenario: string;
  is_edge_case: boolean;
  with_score: number;
  without_score: number;
  delta: number;
  note?: string | null;
}

export interface DeepEvalReport {
  available: boolean;
  reason?: string | null;
  cases: DeepCase[];
  effectiveness_avg: number;
  win_rate: number;
  with_avg: number;
  without_avg: number;
  summary: string;
}

export function useDeepEvaluateConcept(workspaceId: string, path: string) {
  return useMutation<DeepEvalReport, Error, number | void>({
    mutationFn: (n) =>
      unwrap<DeepEvalReport>(
        http.post(`/workspaces/${workspaceId}/concept/deep-evaluate`, null, {
          params: { path, n: n ?? 5 },
        }),
      ),
  });
}

export function searchWorkspace(workspaceId: string, q: string) {
  return unwrap<SearchHit[]>(http.get(`/workspaces/${workspaceId}/search`, { params: { q } }));
}

export { keys as conceptKeys };
