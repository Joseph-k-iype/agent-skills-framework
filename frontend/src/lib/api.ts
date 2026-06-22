const BASE = '/api'

// Optional API key for hosted deployments (matches backend SKILLS_API_KEY).
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
      ...options?.headers,
    },
  })
  if (!res.ok) {
    // FastAPI errors are JSON `{detail: ...}`; fall back to raw text.
    let detail = ''
    const raw = await res.text()
    try {
      const parsed = JSON.parse(raw)
      detail = typeof parsed.detail === 'string' ? parsed.detail : raw
    } catch {
      detail = raw
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`)
  }
  if (res.status === 204) return undefined as T
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
    updateDoc: (name: string, body: string) =>
      fetchJSON<{ body: string; name: string }>(`/skills/${encodeURIComponent(name)}/doc`, {
        method: 'PUT',
        body: JSON.stringify({ body }),
      }),
    versions: (name: string) => fetchJSON<{ name: string; versions: string[]; latest: string; ids: Record<string, string> }>(`/skills/${encodeURIComponent(name)}/versions`),
    validate: (name: string) => fetchJSON<import('./types').ValidationResult>(`/skills/${encodeURIComponent(name)}/validate`, { method: 'POST' }),
    verify: (name: string, version?: string) => {
      const params = version ? `?version=${encodeURIComponent(version)}` : ''
      return fetchJSON<import('./types').VerifyResult>(`/skills/${encodeURIComponent(name)}/verify${params}`, { method: 'POST' })
    },
    build: (path: string) =>
      fetchJSON<{ success: boolean; name?: string; version?: string; id?: string; errors?: string[]; warnings?: string[] }>('/skills/build', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    publish: (path: string, force = false) =>
      fetchJSON<{ success: boolean; name?: string; version?: string; id?: string; path?: string }>('/skills/publish', {
        method: 'POST',
        body: JSON.stringify({ path, force }),
      }),
    install: (name: string, opts: { version?: string; target?: string; verify?: boolean } = {}) =>
      fetchJSON<import('./types').InstallResult>(`/skills/${encodeURIComponent(name)}/install`, {
        method: 'POST',
        body: JSON.stringify({ verify: true, ...opts }),
      }),
    scaffold: (body: import('./types').ScaffoldRequest) =>
      fetchJSON<import('./types').ScaffoldResult>('/skills/scaffold', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    compliance: () => fetchJSON<{ skills: import('./types').ComplianceRow[] }>('/skills/compliance'),
    impact: (name: string) =>
      fetchJSON<import('./types').ImpactResult>(`/skills/${encodeURIComponent(name)}/impact`),
    evaluation: {
      cases: (name: string) =>
        fetchJSON<{ cases: import('./types').EvalCase[] }>(`/skills/${encodeURIComponent(name)}/evaluation/cases`),
      updateCases: (name: string, cases: import('./types').EvalCase[]) =>
        fetchJSON<{ success: boolean; cases: import('./types').EvalCase[] }>(`/skills/${encodeURIComponent(name)}/evaluation/cases`, {
          method: 'PUT',
          body: JSON.stringify({ cases }),
        }),
      run: (name: string, judge?: string | null) =>
        fetchJSON<import('./types').EvaluationReport>(`/skills/${encodeURIComponent(name)}/evaluation/run`, {
          method: 'POST',
          body: JSON.stringify({ judge: judge ?? null }),
        }),
      latest: (name: string, version?: string) => {
        const params = version ? `?version=${encodeURIComponent(version)}` : ''
        return fetchJSON<import('./types').EvaluationReport>(`/skills/${encodeURIComponent(name)}/evaluation/latest${params}`)
      },
      feedback: (name: string) =>
        fetchJSON<import('./types').FeedbackResponse>(`/skills/${encodeURIComponent(name)}/evaluation/feedback`),
      submitFeedback: (
        name: string,
        body: { finding_id: string; finding_signature: string; finding_text: string; verdict: 'accepted' | 'dismissed'; run_id?: string | null },
      ) =>
        fetchJSON<{ success: boolean; entry: import('./types').FeedbackEntry }>(`/skills/${encodeURIComponent(name)}/evaluation/feedback`, {
          method: 'POST',
          body: JSON.stringify(body),
        }),
    },
  },

  audit: {
    list: (limit = 200) => fetchJSON<{ entries: import('./types').AuditEntry[] }>(`/audit?limit=${limit}`),
  },

  deployments: {
    list: () => fetchJSON<import('./types').DeploymentsResponse>('/deployments'),
  },

  registry: {
    info: () => fetchJSON<import('./types').RegistryInfo>('/registry'),
    sources: () => fetchJSON<import('./types').SourceConfig[]>('/registry/sources'),
    addSource: (config: import('./types').HubSourceConfig) =>
      fetchJSON<{ status: string }>('/registry/sources', {
        method: 'POST',
        body: JSON.stringify(config),
      }),
    sync: () => fetchJSON<import('./types').SyncResult>('/registry/sync', { method: 'POST' }),
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
    query: (
      params: { capability?: string; impact_id?: string; permission_resource?: string },
      host = 'localhost',
      port = 6379,
    ) =>
      fetchJSON<import('./types').GraphQueryResult>('/graph/query', {
        method: 'POST',
        body: JSON.stringify({ ...params, host, port }),
      }),
  },
}
