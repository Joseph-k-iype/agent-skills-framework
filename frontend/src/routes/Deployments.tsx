import { useQuery } from '@tanstack/react-query'
import { GitBranch, Globe, Folder, Package, CheckCircle2, XCircle, Clock, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { pluralize, shortHash, formatDate } from '../lib/utils'
import type { DeploymentTarget } from '../lib/types'

export default function Deployments() {
  const { data: sources } = useQuery({
    queryKey: ['registry-sources'],
    queryFn: api.registry.sources,
  })

  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: api.skills.list,
  })

  const entries = Object.entries(skills ?? {})

  const targets: DeploymentTarget[] = (sources ?? []).map((s, i) => ({
    name: s.url || s.path || `source-${i}`,
    type: s.type as 'local' | 'git',
    status: 'active' as const,
    skillCount: entries.length,
    lastSync: new Date().toISOString(),
    url: s.url,
    path: s.path,
  }))

  if (targets.length === 0) {
    targets.push({
      name: 'Local Registry',
      type: 'local',
      status: 'active',
      skillCount: entries.length,
      lastSync: new Date().toISOString(),
      path: './registry',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Deployments</h2>
          <p className="mt-1 text-sm text-gray-400">
            Manage skill deployment targets and status
          </p>
        </div>
        <button className="btn-secondary">
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Targets', value: targets.length, icon: Globe, color: 'text-brand-400 bg-brand-600/10' },
          { label: 'Skills Deployed', value: entries.length, icon: Package, color: 'text-emerald-400 bg-emerald-600/10' },
          { label: 'Active', value: targets.filter(t => t.status === 'active').length, icon: CheckCircle2, color: 'text-emerald-400 bg-emerald-600/10' },
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

      <div className="space-y-3">
        {targets.map((target) => (
          <div key={target.name} className="card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                  target.type === 'git' ? 'bg-amber-600/20 text-amber-400' : 'bg-brand-600/20 text-brand-400'
                }`}>
                  {target.type === 'git' ? <GitBranch size={20} /> : <Folder size={20} />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-200">{target.name}</p>
                    <span className={`badge ${
                      target.status === 'active' ? 'bg-emerald-600/10 text-emerald-400' :
                      target.status === 'error' ? 'bg-red-600/10 text-red-400' :
                      'bg-gray-800 text-gray-500'
                    }`}>
                      {target.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {target.url || target.path} · {pluralize(target.skillCount, 'skill')}
                    {target.lastSync && ` · synced ${formatDate(target.lastSync)}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">{target.type}</span>
              </div>
            </div>

            <div className="mt-3 border-t border-gray-800 pt-3">
              <h4 className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Deployed Skills
              </h4>
              {entries.length === 0 ? (
                <p className="text-xs text-gray-600">No skills deployed</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {entries.map(([name, info]) => (
                    <div key={name} className="flex items-center gap-1.5 rounded-md border border-gray-800 bg-gray-900 px-2 py-1">
                      <Package size={10} className="text-brand-400" />
                      <span className="text-xs text-gray-300">{name}</span>
                      <span className="text-[10px] text-gray-600">v{info.latest}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
