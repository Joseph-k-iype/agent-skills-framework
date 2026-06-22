import { useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch, Globe, Folder, Package, CheckCircle2, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { pluralize, formatDate } from '../lib/utils'
import ErrorState from '../components/ErrorState'

export default function Deployments() {
  const queryClient = useQueryClient()

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ['deployments'],
    queryFn: api.deployments.list,
  })

  const targets = data?.targets ?? []
  const skills = data?.skills ?? []

  const stats = [
    { label: 'Targets', value: targets.length, icon: Globe },
    { label: 'Skills', value: data?.total_skills ?? 0, icon: Package },
    { label: 'Active', value: targets.filter((t) => t.status === 'active').length, icon: CheckCircle2 },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Overview</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Deployments</h2>
          <p className="mt-2 text-sm text-ink-2">
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
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="card">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
                <Icon size={20} />
              </div>
              <div>
                <p className="eyebrow">{label}</p>
                <p className="mt-1 text-2xl font-light tabular-nums tracking-tightish text-ink">{isLoading ? '...' : value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {isError ? (
        <ErrorState error={error} onRetry={refetch} title="Couldn't load deployments" />
      ) : !isLoading && targets.length === 0 ? (
        <div className="card py-16 text-center">
          <Globe size={48} className="mx-auto text-ink-3" />
          <p className="mt-4 text-lg font-medium text-ink-2">No deployment targets</p>
          <p className="mt-1 text-sm text-ink-3">
            Configure a registry source to see deployment targets here
          </p>
        </div>
      ) : (
      <div className="space-y-3">
        {targets.map((target) => (
          <div key={target.name} className="card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
                  {target.type === 'git' ? <GitBranch size={20} /> : <Folder size={20} />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-ink break-all">{target.name}</p>
                    <span className="inline-flex items-center gap-1.5 text-xs text-ink-2">
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        target.status === 'active' ? 'bg-ok' :
                        target.status === 'error' ? 'bg-bad' :
                        'bg-warn'
                      }`} />
                      {target.status}
                    </span>
                  </div>
                  <p className="font-mono text-xs text-ink-3">
                    {target.url || target.path}
                    {target.skillCount != null && ` · ${pluralize(target.skillCount, 'skill')}`}
                    {target.lastSync && ` · synced ${formatDate(target.lastSync)}`}
                  </p>
                </div>
              </div>
              <span className="text-xs text-ink-3">{target.type}</span>
            </div>

            {/* Only the local registry can attribute the concrete skill set. */}
            {target.type === 'local' && target.skillCount != null && (
              <div className="mt-3 border-t border-line pt-3">
                <h4 className="eyebrow mb-2">
                  Deployed Skills
                </h4>
                {skills.length === 0 ? (
                  <p className="text-xs text-ink-3">No skills deployed</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {skills.map((s) => (
                      <div key={s.name} className="flex items-center gap-1.5 rounded-md border border-line bg-canvas px-2 py-1">
                        <Package size={10} className="text-ink-2" />
                        <span className="text-xs text-ink">{s.name}</span>
                        <span className="font-mono text-[10px] text-ink-3">v{s.latest}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      )}
    </div>
  )
}
