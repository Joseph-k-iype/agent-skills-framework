import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface Workspace {
  id: string;
  name: string;
  description?: string | null;
  owner?: string | null;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Folder {
  id: string;
  name: string;
  path?: string | null;
  workspace_id: string;
  parent_id?: string | null;
  status: string;
}

export interface WorkspaceTree {
  workspace: Workspace;
  folders: Folder[];
}

const keys = {
  list: ["workspaces"] as const,
  tree: (id: string) => ["workspace", id] as const,
};

export function useWorkspaces() {
  return useQuery({
    queryKey: keys.list,
    queryFn: () => unwrap<Workspace[]>(http.get("/workspaces")),
  });
}

export function useWorkspaceTree(id: string | undefined) {
  return useQuery({
    queryKey: keys.tree(id ?? ""),
    queryFn: () => unwrap<WorkspaceTree>(http.get(`/workspaces/${id}`)),
    enabled: !!id,
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      unwrap<Workspace>(http.post("/workspaces", body)),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list }),
  });
}

export function useCreateFolder(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; parent_id: string }) =>
      unwrap<Folder>(http.post("/folders", { ...body, workspace_id: workspaceId })),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.tree(workspaceId) }),
  });
}

export function useRenameFolder(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      unwrap<Folder>(http.patch(`/folders/${id}`, { name })),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.tree(workspaceId) }),
  });
}

export function useDeleteFolder(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(http.delete(`/folders/${id}`)),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.tree(workspaceId) }),
  });
}

/** Move a folder with optimistic update + rollback on error. */
export function useMoveFolder(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, new_parent_id }: { id: string; new_parent_id: string }) =>
      unwrap<Folder>(http.post(`/folders/${id}/move`, { new_parent_id })),
    onMutate: async ({ id, new_parent_id }) => {
      await qc.cancelQueries({ queryKey: keys.tree(workspaceId) });
      const prev = qc.getQueryData<WorkspaceTree>(keys.tree(workspaceId));
      if (prev) {
        qc.setQueryData<WorkspaceTree>(keys.tree(workspaceId), {
          ...prev,
          folders: prev.folders.map((f) =>
            f.id === id ? { ...f, parent_id: new_parent_id } : f,
          ),
        });
      }
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(keys.tree(workspaceId), ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: keys.tree(workspaceId) }),
  });
}

export { keys as workspaceKeys };
