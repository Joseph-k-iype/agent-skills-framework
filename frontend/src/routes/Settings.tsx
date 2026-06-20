import { useQuery } from '@tanstack/react-query'
import { Settings as SettingsIcon, Folder, GitBranch, Database, Shield, Info, FileJson, User } from 'lucide-react'
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
          <h2 className="text-2xl font-bold text-gray-100">Settings</h2>
          <p className="mt-1 text-sm text-gray-400">
            Framework configuration and preferences
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <Info size={14} /> Framework
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Version', value: '0.1.0' },
              { label: 'API Version', value: '1' },
              { label: 'Registry Schema', value: `v${info?.schema_version ?? '?'}` },
              { label: 'Skills', value: String(info?.skill_count ?? 0) },
              { label: 'Sources', value: String(info?.sources?.length ?? 0) },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between rounded-lg border border-gray-800 p-3">
                <span className="text-sm text-gray-400">{label}</span>
                <span className="text-sm font-medium text-gray-200">{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <Database size={14} /> Registry
          </h3>
          <div className="space-y-3">
            <div className="rounded-lg border border-gray-800 p-3">
              <p className="text-sm text-gray-400">Index File</p>
              <p className="mt-1 text-sm font-mono text-gray-200">index.yaml</p>
            </div>
            <div className="rounded-lg border border-gray-800 p-3">
              <p className="text-sm text-gray-400">Workspace</p>
              <p className="mt-1 text-sm font-mono text-gray-200 break-all">{info?.workspace ?? '...'}</p>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-gray-800 p-3">
              <span className="text-sm text-gray-400">Auto-tag on Publish</span>
              <span className={`badge ${info?.auto_tag ? 'bg-emerald-600/10 text-emerald-400' : 'bg-gray-800 text-gray-400'}`}>
                {info ? (info.auto_tag ? 'Enabled' : 'Disabled') : '...'}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-gray-800 p-3">
              <span className="text-sm text-gray-400">API Authentication</span>
              <span className={`badge ${info?.auth_required ? 'bg-emerald-600/10 text-emerald-400' : 'bg-amber-600/10 text-amber-400'}`}>
                {info ? (info.auth_required ? 'Required' : 'Open (dev)') : '...'}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <GitBranch size={14} /> Sources
          </h3>
          {!sources?.length ? (
            <div className="py-8 text-center">
              <Folder size={32} className="mx-auto text-gray-600" />
              <p className="mt-2 text-sm text-gray-500">No sources configured</p>
            </div>
          ) : (
            <div className="space-y-2">
              {sources.map((source, i) => (
                <div key={i} className="rounded-lg border border-gray-800 p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {source.type === 'git' ? (
                        <GitBranch size={14} className="text-amber-400" />
                      ) : (
                        <Folder size={14} className="text-brand-400" />
                      )}
                      <span className="text-sm font-medium text-gray-200 capitalize">{source.type}</span>
                    </div>
                    <span className="badge bg-gray-800 text-gray-400">{source.type === 'git' ? source.ref : 'local'}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 font-mono">{source.url || source.path}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <Shield size={14} /> Governance
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Require Hash Verification', value: 'Enabled' },
              { label: 'Enforce Valid Manifests', value: 'Enabled' },
              { label: 'Dependency Cycle Detection', value: 'Enabled' },
              { label: 'Permission Validation', value: 'Enabled' },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between rounded-lg border border-gray-800 p-3">
                <span className="text-sm text-gray-400">{label}</span>
                <span className="badge bg-emerald-600/10 text-emerald-400">{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <User size={14} /> User Role
          </h3>
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-amber-600/10 p-3 text-xs text-amber-400">
            <Shield size={14} className="mt-0.5 shrink-0" />
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
                    ? 'border-brand-600/50 bg-brand-600/5'
                    : 'border-gray-800 hover:bg-gray-800/50'
                }`}
              >
                <input
                  type="radio"
                  name="role"
                  value={opt.value}
                  checked={role === opt.value}
                  onChange={() => setRole(opt.value)}
                  className="h-4 w-4 border-gray-600 text-brand-600"
                />
                <div>
                  <p className="text-sm font-medium text-gray-200">{opt.label}</p>
                  <p className="text-xs text-gray-500">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
