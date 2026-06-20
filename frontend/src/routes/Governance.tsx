import { useQuery } from '@tanstack/react-query'
import { Shield, CheckCircle2, XCircle, AlertTriangle, Package, FileKey, Lock, Eye } from 'lucide-react'
import { api } from '../lib/api'
import { pluralize } from '../lib/utils'

export default function Governance() {
  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: api.skills.list,
  })

  const entries = Object.entries(skills ?? {})

  const { data: validations } = useQuery({
    queryKey: ['skill-validations'],
    queryFn: async () => {
      const results: Record<string, boolean> = {}
      for (const [name] of entries) {
        try {
          const r = await api.skills.validate(name)
          results[name] = r.valid
        } catch {
          results[name] = false
        }
      }
      return results
    },
    enabled: entries.length > 0,
  })

  const validCount = Object.values(validations ?? {}).filter(Boolean).length
  const failCount = Object.values(validations ?? {}).filter((v) => !v).length

  const { data: manifests } = useQuery({
    queryKey: ['all-manifests'],
    queryFn: async () => {
      const results: Record<string, any> = {}
      for (const [name] of entries) {
        try {
          const m = await api.skills.manifest(name)
          results[name] = m.manifest
        } catch {
          // skip
        }
      }
      return results
    },
    enabled: entries.length > 0,
  })

  const totalPermissions = manifests
    ? Object.values(manifests).reduce((sum, m: any) => sum + (m.permissions?.length ?? 0), 0)
    : 0
  const totalCapabilities = manifests
    ? Object.values(manifests).reduce((sum, m: any) => sum + (m.capabilities?.length ?? 0), 0)
    : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Governance</h2>
          <p className="mt-1 text-sm text-gray-400">
            Compliance, permissions, and policy overview
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Skills', value: entries.length, icon: Package, color: 'text-brand-400 bg-brand-600/10' },
          { label: 'Passing', value: validCount, icon: CheckCircle2, color: 'text-emerald-400 bg-emerald-600/10' },
          { label: 'Failing', value: failCount, icon: XCircle, color: 'text-red-400 bg-red-600/10' },
          { label: 'Capabilities', value: totalCapabilities, icon: FileKey, color: 'text-amber-400 bg-amber-600/10' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold text-gray-100">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <Shield size={14} /> Policy Compliance
          </h3>
          <div className="space-y-3">
            {[
              { name: 'Valid Manifest', pass: validCount, total: entries.length, status: failCount === 0 ? 'pass' : failCount > 0 ? 'warn' : 'unknown' },
              { name: 'Content Hash Integrity', pass: validCount, total: entries.length, status: failCount === 0 ? 'pass' : 'warn' },
              { name: 'Permission Declarations', pass: totalPermissions > 0 ? entries.length : 0, total: entries.length, status: entries.length > 0 && totalPermissions === 0 ? 'warn' : 'pass' },
            ].map((policy) => (
              <div key={policy.name} className="flex items-center justify-between rounded-lg border border-gray-800 p-3">
                <div className="flex items-center gap-3">
                  {policy.status === 'pass' ? (
                    <CheckCircle2 size={16} className="text-emerald-400" />
                  ) : policy.status === 'warn' ? (
                    <AlertTriangle size={16} className="text-amber-400" />
                  ) : (
                    <AlertTriangle size={16} className="text-gray-600" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-200">{policy.name}</p>
                    <p className="text-xs text-gray-500">
                      {policy.pass}/{policy.total} passing
                    </p>
                  </div>
                </div>
                <span className={`badge ${
                  policy.status === 'pass' ? 'bg-emerald-600/10 text-emerald-400' :
                  policy.status === 'warn' ? 'bg-amber-600/10 text-amber-400' :
                  'bg-gray-800 text-gray-500'
                }`}>
                  {policy.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <Lock size={14} /> Permissions Summary
          </h3>
          {!manifests || Object.keys(manifests).length === 0 ? (
            <div className="py-8 text-center">
              <Lock size={32} className="mx-auto text-gray-600" />
              <p className="mt-2 text-sm text-gray-500">No permissions declared</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {Object.entries(manifests).map(([name, m]: [string, any]) =>
                m.permissions?.map((p: any, i: number) => (
                  <div key={`${name}-${i}`} className="flex items-center justify-between rounded-lg border border-gray-800 p-2">
                    <div className="flex items-center gap-2">
                      <Eye size={12} className="text-gray-500" />
                      <span className="text-sm text-gray-300">{p.resource}</span>
                    </div>
                    <div className="flex gap-1">
                      {p.actions?.map((a: string) => (
                        <span key={a} className="badge bg-gray-800 text-gray-400 text-[10px]">{a}</span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="mb-4 text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Skill Compliance
        </h3>
        {entries.length === 0 ? (
          <div className="py-8 text-center">
            <Package size={32} className="mx-auto text-gray-600" />
            <p className="mt-2 text-sm text-gray-500">No skills in registry</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                  <th className="pb-2 pr-4 font-medium">Skill</th>
                  <th className="pb-2 pr-4 font-medium">Runtime</th>
                  <th className="pb-2 pr-4 font-medium">Permissions</th>
                  <th className="pb-2 pr-4 font-medium">Capabilities</th>
                  <th className="pb-2 font-medium">Compliance</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(([name, info]) => {
                  const m = manifests?.[name] as any
                  const isValid = validations?.[name]
                  return (
                    <tr key={name} className="border-b border-gray-800/50">
                      <td className="py-3 pr-4">
                        <p className="font-medium text-gray-200">{name}</p>
                        <p className="text-xs text-gray-500">v{info.latest}</p>
                      </td>
                      <td className="py-3 pr-4">
                        {m?.runtime && (
                          <span className="tag bg-gray-800 text-gray-300">{m.runtime}</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-gray-400">
                        {m?.permissions?.length ?? 0}
                      </td>
                      <td className="py-3 pr-4 text-gray-400">
                        {m?.capabilities?.length ?? 0}
                      </td>
                      <td className="py-3">
                        {isValid === undefined ? (
                          <span className="text-gray-600">...</span>
                        ) : isValid ? (
                          <span className="badge bg-emerald-600/10 text-emerald-400">Valid</span>
                        ) : (
                          <span className="badge bg-red-600/10 text-red-400">Invalid</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
