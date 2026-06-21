import { useQuery } from '@tanstack/react-query'
import { Folder, GitBranch, Database, Shield, Info, User } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth, roleOptions } from '../lib/auth'

export default function Settings() {
  const { role, setRole } = useAuth()
  const { data: info } = useQuery({
    queryKey: ['registry-info'],
    queryFn: api.registry.info,
  })

  const { data: sources } = useQuery({
    queryKey: ['registry-sources'],
    queryFn: api.registry.sources,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Configuration</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Settings</h2>
          <p className="mt-2 text-sm text-ink-2">
            Framework configuration and preferences
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <Info size={14} /> Framework
          </h3>
          <div className="divide-y divide-line">
            {[
              { label: 'Version', value: '0.1.0' },
              { label: 'API Version', value: '1' },
              { label: 'Registry Schema', value: `v${info?.schema_version ?? '?'}` },
              { label: 'Skills', value: String(info?.skill_count ?? 0) },
              { label: 'Sources', value: String(info?.sources?.length ?? 0) },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between py-3">
                <span className="text-sm text-ink-3">{label}</span>
                <span className="text-sm font-medium text-ink">{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <Database size={14} /> Registry
          </h3>
          <div className="divide-y divide-line">
            <div className="py-3">
              <p className="text-sm text-ink-3">Index File</p>
              <p className="mt-1 text-sm font-mono text-ink">index.yaml</p>
            </div>
            <div className="py-3">
              <p className="text-sm text-ink-3">Workspace</p>
              <p className="mt-1 text-sm font-mono text-ink break-all">{info?.workspace ?? '...'}</p>
            </div>
            <div className="flex items-center justify-between py-3">
              <span className="text-sm text-ink-3">Auto-tag on Publish</span>
              <span className="badge gap-1.5 border border-line bg-canvas text-ink-2">
                <span className={`h-1.5 w-1.5 rounded-full ${info?.auto_tag ? 'bg-ok' : 'bg-ink-3'}`} />
                {info ? (info.auto_tag ? 'Enabled' : 'Disabled') : '...'}
              </span>
            </div>
            <div className="flex items-center justify-between py-3">
              <span className="text-sm text-ink-3">API Authentication</span>
              <span className="badge gap-1.5 border border-line bg-canvas text-ink-2">
                <span className={`h-1.5 w-1.5 rounded-full ${info?.auth_required ? 'bg-ok' : 'bg-warn'}`} />
                {info ? (info.auth_required ? 'Required' : 'Open (dev)') : '...'}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <GitBranch size={14} /> Sources
          </h3>
          {!sources?.length ? (
            <div className="py-8 text-center">
              <Folder size={32} className="mx-auto text-ink-3" />
              <p className="mt-2 text-sm text-ink-2">No sources configured</p>
            </div>
          ) : (
            <div className="space-y-2">
              {sources.map((source, i) => (
                <div key={i} className="rounded-lg border border-line p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {source.type === 'git' ? (
                        <GitBranch size={14} className="text-ink-2" />
                      ) : (
                        <Folder size={14} className="text-ink-2" />
                      )}
                      <span className="text-sm font-medium text-ink capitalize">{source.type}</span>
                    </div>
                    <span className="badge border border-line bg-canvas text-ink-2">{source.type === 'git' ? source.ref : 'local'}</span>
                  </div>
                  <p className="mt-1 text-xs text-ink-3 font-mono">{source.url || source.path}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <Shield size={14} /> Governance
          </h3>
          <div className="divide-y divide-line">
            {[
              { label: 'Require Hash Verification', value: 'Enabled' },
              { label: 'Enforce Valid Manifests', value: 'Enabled' },
              { label: 'Dependency Cycle Detection', value: 'Enabled' },
              { label: 'Permission Validation', value: 'Enabled' },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between py-3">
                <span className="text-sm text-ink-3">{label}</span>
                <span className="badge gap-1.5 border border-line bg-canvas text-ink-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <User size={14} /> User Role
          </h3>
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-line bg-canvas p-3 text-xs text-ink-2">
            <Shield size={14} className="mt-0.5 shrink-0 text-ink-3" />
            <span>
              Client-side preview only. This switches which UI is permission-gated; it is
              <strong> not</strong> an authorization boundary. Real authz is enforced server-side
              via the API key — see docs/security.md.
            </span>
          </div>
          <div className="space-y-2">
            {roleOptions.map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition ${
                  role === opt.value
                    ? 'border-accent-300 bg-accent-50'
                    : 'border-line hover:bg-canvas'
                }`}
              >
                <input
                  type="radio"
                  name="role"
                  value={opt.value}
                  checked={role === opt.value}
                  onChange={() => setRole(opt.value)}
                  className="h-4 w-4 border-line text-accent-500 focus:ring-accent-500/15"
                />
                <div>
                  <p className="text-sm font-medium text-ink">{opt.label}</p>
                  <p className="text-xs text-ink-3">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
