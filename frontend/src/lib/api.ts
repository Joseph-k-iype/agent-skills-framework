const BASE = '/api'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

export const api = {
  dashboard: {
    stats: () => fetchJSON<import('./types').DashboardStats>('/dashboard/stats'),
  },

  skills: {
    list: () => fetchJSON<Record<string, import('./types').SkillEntry>>('/skills'),
    detail: (name: string) => fetchJSON<import('./types').SkillEntry & { name: string }>(`/skills/${encodeURIComponent(name)}`),
    manifest: (name: string) => fetchJSON<import('./types').ManifestResponse>(`/skills/${encodeURIComponent(name)}/manifest`),
    doc: (name: string, format = 'markdown') => fetchJSON<import('./types').DocResult>(`/skills/${encodeURIComponent(name)}/doc?format=${format}`),
    versions: (name: string) => fetchJSON<{ name: string; versions: string[]; latest: string; ids: Record<string, string> }>(`/skills/${encodeURIComponent(name)}/versions`),
    validate: (name: string) => fetchJSON<import('./types').ValidationResult>(`/skills/${encodeURIComponent(name)}/validate`, { method: 'POST' }),
    verify: (name: string, version?: string) => {
      const params = version ? `?version=${encodeURIComponent(version)}` : ''
      return fetchJSON<import('./types').VerifyResult>(`/skills/${encodeURIComponent(name)}/verify${params}`, { method: 'POST' })
    },
    build: (path: string) =>
      fetchJSON<{ success: boolean; name?: string; version?: string; id?: string; errors?: string[] }>('/skills/build', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    publish: (path: string, force = false) =>
      fetchJSON<{ success: boolean; name?: string; version?: string; id?: string; path?: string }>('/skills/publish', {
        method: 'POST',
        body: JSON.stringify({ path, force }),
      }),
  },

  registry: {
    info: () => fetchJSON<import('./types').RegistryInfo>('/registry'),
    sources: () => fetchJSON<import('./types').SourceConfig[]>('/registry/sources'),
    addSource: (config: import('./types').HubSourceConfig) =>
      fetchJSON<{ status: string }>('/registry/sources', {
        method: 'POST',
        body: JSON.stringify(config),
      }),
    sync: () => fetchJSON<{ synced: number; skills: string[] }>('/registry/sync', { method: 'POST' }),
  },

  graph: {
    connect: (host = 'localhost', port = 6379) =>
      fetchJSON<{ connected: boolean }>('/graph/connect', {
        method: 'POST',
        body: JSON.stringify({ host, port }),
      }),
    register: (manifestPath: string, host = 'localhost', port = 6379) =>
      fetchJSON<{ status: string }>('/graph/register', {
        method: 'POST',
        body: JSON.stringify({ host, port, manifest_path: manifestPath }),
      }),
    query: (params: { capability?: string; impact_id?: string }) =>
      fetchJSON<import('./types').GraphQueryResult>('/graph/query', {
        method: 'POST',
        body: JSON.stringify({ ...params, host: 'localhost', port: 6379 }),
      }),
  },
}
