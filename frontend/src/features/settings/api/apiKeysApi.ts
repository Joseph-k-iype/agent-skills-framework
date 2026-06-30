import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  last_used_at?: string | null;
  created_at?: string | null;
}

export interface CreatedApiKey extends ApiKey {
  key: string; // shown once
}

export function useApiKeys() {
  return useQuery({
    queryKey: ["api-keys"],
    queryFn: () => unwrap<ApiKey[]>(http.get(`/api-keys`)),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation<CreatedApiKey, Error, string>({
    mutationFn: (name) => unwrap<CreatedApiKey>(http.post(`/api-keys`, { name })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation<{ revoked: string }, Error, string>({
    mutationFn: (id) => unwrap(http.delete(`/api-keys/${id}`)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}
