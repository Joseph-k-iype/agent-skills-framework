import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface SkillRef {
  id: string;
  title?: string;
}

export interface Skill {
  id: string;
  skill_key: string;
  name: string;
  description?: string | null;
  runtime: string;
  version: string;
  status: string;
  is_current: boolean;
  workspace_id?: string | null;
  folder_id?: string | null;
  tags: string[];
  capabilities: string[];
  references: SkillRef[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SkillVersions {
  skill_key: string;
  versions: Skill[];
}

const keys = {
  list: (workspaceId?: string) => ["skills", workspaceId ?? "all"] as const,
  one: (id: string) => ["skill", id] as const,
  versions: (id: string) => ["skill-versions", id] as const,
};

export function useSkills(workspaceId?: string) {
  return useQuery({
    queryKey: keys.list(workspaceId),
    queryFn: () =>
      unwrap<Skill[]>(http.get("/skills", { params: workspaceId ? { workspace_id: workspaceId } : {} })),
  });
}

export function useSkill(id: string | undefined) {
  return useQuery({
    queryKey: keys.one(id ?? ""),
    queryFn: () => unwrap<Skill>(http.get(`/skills/${id}`)),
    enabled: !!id,
  });
}

export function useSkillVersions(id: string | undefined) {
  return useQuery({
    queryKey: keys.versions(id ?? ""),
    queryFn: () => unwrap<SkillVersions>(http.get(`/skills/${id}/versions`)),
    enabled: !!id,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      folder_id: string;
      workspace_id?: string;
      description?: string;
      runtime?: string;
      capabilities?: string[];
    }) => unwrap<Skill>(http.post("/skills", body)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export function useUpdateSkill(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<Skill, "name" | "description" | "runtime" | "tags" | "capabilities">> & {
      references?: string[];
    }) => unwrap<Skill>(http.patch(`/skills/${id}`, body)),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: keys.one(id) });
      qc.invalidateQueries({ queryKey: ["skills"] });
      return s;
    },
  });
}

export function usePublishSkill(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { version?: string }) => unwrap<Skill>(http.post(`/skills/${id}/publish`, body)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skill"] });
      qc.invalidateQueries({ queryKey: ["skill-versions"] });
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useDeleteSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(http.delete(`/skills/${id}`)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export { keys as skillKeys };
