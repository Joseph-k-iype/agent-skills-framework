import { useQuery } from '@tanstack/react-query'
import { Shield, CheckCircle2, XCircle, AlertTriangle, Package, FileKey, Lock } from 'lucide-react'
import { api } from '../lib/api'

export default function Governance() {
  // Single backend call returns per-skill compliance — no more N+1 waterfall of
  // validate+manifest requests from the browser.
  const { data, isLoading } = useQuery({
    queryKey: ['compliance'],
    queryFn: api.skills.compliance,
  })

  const rows = data?.skills ?? []
  const validCount = rows.filter((r) => r.valid === true).length
  const failCount = rows.filter((r) => r.valid === false).length
  const totalPermissions = rows.reduce((s, r) => s + r.permissions, 0)
  const totalCapabilities = rows.reduce((s, r) => s + r.capabilities, 0)

  const stats = [
    { label: 'Skills', value: rows.length, icon: Package, color: 'text-brand-400 bg-brand-600/10' },
    { label: 'Passing', value: validCount, icon: CheckCircle2, color: 'text-emerald-400 bg-emerald-600/10' },
    { label: 'Failing', value: failCount, icon: XCircle, color: 'text-red-400 bg-red-600/10' },
    { label: 'Capabilities', value: totalCapabilities, icon: FileKey, color: 'text-amber-400 bg-amber-600/10' },
  ]

  const policies = [
    {
      name: 'Valid Manifest',
      pass: validCount,
      total: rows.length,
      status: rows.length === 0 ? 'unknown' : failCount === 0 ? 'pass' : 'warn',
    },
    {
      name: 'Content Hash Integrity',
      pass: validCount,
      total: rows.length,
      status: rows.length === 0 ? 'unknown' : failCount === 0 ? 'pass' : 'warn',
    },
    {
      name: 'Permission Declarations',
      pass: rows.filter((r) => r.permissions > 0).length,
      total: rows.length,
      status: rows.length > 0 && totalPermissions === 0 ? 'warn' : 'pass',
    },
  ] as const

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Governance</h2>
        <p className="mt-1 text-sm text-gray-400">Compliance, permissions, and policy overview</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold text-gray-100">{isLoading ? '...' : value}</p>
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
            {policies.map((policy) => (
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
                    <p className="text-xs text-gray-500">{policy.pass}/{policy.total} passing</p>
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
            <Lock size={14} /> Permissions &amp; Capabilities
          </h3>
          {rows.length === 0 ? (
            <div className="py-8 text-center">
              <Lock size={32} className="mx-auto text-gray-600" />
              <p className="mt-2 text-sm text-gray-500">No skills in registry</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {rows.map((r) => (
                <div key={r.name} className="flex items-center justify-between rounded-lg border border-gray-800 p-2">
                  <span className="text-sm text-gray-300">{r.name}</span>
                  <div className="flex gap-2">
                    <span className="badge bg-gray-800 text-gray-400 text-[10px]">{r.permissions} perms</span>
                    <span className="badge bg-gray-800 text-gray-400 text-[10px]">{r.capabilities} caps</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="mb-4 text-sm font-semibold text-gray-300 uppercase tracking-wider">Skill Compliance</h3>
        {rows.length === 0 ? (
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
                {rows.map((r) => (
                  <tr key={r.name} className="border-b border-gray-800/50">
                    <td className="py-3 pr-4">
                      <p className="font-medium text-gray-200">{r.name}</p>
                      <p className="text-xs text-gray-500">v{r.latest}</p>
                    </td>
                    <td className="py-3 pr-4">
                      {r.runtime && <span className="tag bg-gray-800 text-gray-300">{r.runtime}</span>}
                    </td>
                    <td className="py-3 pr-4 text-gray-400">{r.permissions}</td>
                    <td className="py-3 pr-4 text-gray-400">{r.capabilities}</td>
                    <td className="py-3">
                      {r.valid === null ? (
                        <span className="text-gray-600">—</span>
                      ) : r.valid ? (
                        <span className="badge bg-emerald-600/10 text-emerald-400">Valid</span>
                      ) : (
                        <span className="badge bg-red-600/10 text-red-400" title={r.errors.join('; ')}>Invalid</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
