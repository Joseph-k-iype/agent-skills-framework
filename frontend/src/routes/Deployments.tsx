import { useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch, Globe, Folder, Package, CheckCircle2, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { pluralize, formatDate } from '../lib/utils'

export default function Deployments() {
  const queryClient = useQueryClient()

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['deployments'],
    queryFn: api.deployments.list,
  })

  const targets = data?.targets ?? []
  const skills = data?.skills ?? []

  const stats = [
    { label: 'Targets', value: targets.length, icon: Globe, color: 'text-brand-400 bg-brand-600/10' },
    { label: 'Skills', value: data?.total_skills ?? 0, icon: Package, color: 'text-emerald-400 bg-emerald-600/10' },
    { label: 'Active', value: targets.filter((t) => t.status === 'active').length, icon: CheckCircle2, color: 'text-emerald-400 bg-emerald-600/10' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Deployments</h2>
          <p className="mt-1 text-sm text-gray-400">
            Targets derived from the registry and its configured sources
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => queryClient.invalidateQueries({ queryKey: ['deployments'] })}
          disabled={isFetching}
        >
          <RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
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
                    <p className="text-sm font-semibold text-gray-200 break-all">{target.name}</p>
                    <span className={`badge ${
                      target.status === 'active' ? 'bg-emerald-600/10 text-emerald-400' :
                      target.status === 'error' ? 'bg-red-600/10 text-red-400' :
                      'bg-gray-800 text-gray-400'
                    }`}>
                      {target.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {target.url || target.path}
                    {target.skillCount != null && ` · ${pluralize(target.skillCount, 'skill')}`}
                    {target.lastSync && ` · synced ${formatDate(target.lastSync)}`}
                  </p>
                </div>
              </div>
              <span className="text-xs text-gray-500">{target.type}</span>
            </div>

            {/* Only the local registry can attribute the concrete skill set. */}
            {target.type === 'local' && target.skillCount != null && (
              <div className="mt-3 border-t border-gray-800 pt-3">
                <h4 className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Deployed Skills
                </h4>
                {skills.length === 0 ? (
                  <p className="text-xs text-gray-600">No skills deployed</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {skills.map((s) => (
                      <div key={s.name} className="flex items-center gap-1.5 rounded-md border border-gray-800 bg-gray-900 px-2 py-1">
                        <Package size={10} className="text-brand-400" />
                        <span className="text-xs text-gray-300">{s.name}</span>
                        <span className="text-[10px] text-gray-600">v{s.latest}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
