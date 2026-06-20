import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Clock, CheckCircle2, XCircle, Info, Package, Layers, Filter } from 'lucide-react'
import { api } from '../lib/api'
import { formatDate, shortHash } from '../lib/utils'
import type { AuditEntry } from '../lib/types'

export default function AuditLog() {
  const [filter, setFilter] = useState<string>('all')

  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: api.skills.list,
  })

  const entries = Object.entries(skills ?? {})

  const { data: versionHistories } = useQuery({
    queryKey: ['all-versions'],
    queryFn: async () => {
      const results: Record<string, { version: string; id: string }[]> = {}
      for (const [name] of entries) {
        try {
          const v = await api.skills.versions(name)
          results[name] = v.versions.map((ver) => ({
            version: ver,
            id: v.ids?.[ver] ?? '',
          }))
        } catch {
          results[name] = []
        }
      }
      return results
    },
    enabled: entries.length > 0,
  })

  const auditLog: AuditEntry[] = []
  if (versionHistories) {
    for (const [name, versions] of Object.entries(versionHistories)) {
      for (const v of versions) {
        auditLog.push({
          id: `${name}-${v.version}-publish`,
          action: 'Skill Published',
          skillName: name,
          version: v.version,
          timestamp: new Date().toISOString(),
          status: 'success',
          details: `Published ${name}@${v.version} with hash ${shortHash(v.id)}`,
        })
      }
    }
  }

  auditLog.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  const filtered = filter === 'all' ? auditLog : auditLog.filter((e) => e.action.toLowerCase().includes(filter))

  const filters = [
    { key: 'all', label: 'All Events', count: auditLog.length },
    { key: 'publish', label: 'Publishes', count: auditLog.filter((e) => e.action === 'Skill Published').length },
    { key: 'success', label: 'Success', count: auditLog.filter((e) => e.status === 'success').length },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Audit Log</h2>
          <p className="mt-1 text-sm text-gray-400">
            Track skill operations and changes
          </p>
        </div>
      </div>

      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`btn-ghost text-xs ${filter === f.key ? 'text-brand-400 bg-brand-600/10' : ''}`}
          >
            {f.label}
            <span className="ml-1.5 text-gray-500">({f.count})</span>
          </button>
        ))}
      </div>

      {auditLog.length === 0 ? (
        <div className="card py-16 text-center">
          <Clock size={48} className="mx-auto text-gray-700" />
          <p className="mt-4 text-lg font-medium text-gray-400">No audit entries</p>
          <p className="mt-1 text-sm text-gray-500">
            Publish or validate skills to see activity here
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          {filtered.map((entry, i) => (
            <div key={entry.id} className="card-hover flex items-start gap-4">
              <div className="relative flex flex-col items-center">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                  entry.status === 'success' ? 'bg-emerald-600/10 text-emerald-400' :
                  entry.status === 'error' ? 'bg-red-600/10 text-red-400' :
                  'bg-brand-600/10 text-brand-400'
                }`}>
                  {entry.status === 'success' ? <CheckCircle2 size={14} /> :
                   entry.status === 'error' ? <XCircle size={14} /> :
                   <Info size={14} />}
                </div>
                {i < filtered.length - 1 && (
                  <div className="mt-1 w-px flex-1 bg-gray-800" />
                )}
              </div>
              <div className="flex-1 pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-gray-200">{entry.action}</p>
                    <span className="badge bg-brand-600/10 text-brand-400">{entry.skillName}</span>
                    {entry.version && (
                      <span className="text-xs text-gray-500">v{entry.version}</span>
                    )}
                  </div>
                  <span className="text-xs text-gray-600">{formatDate(entry.timestamp)}</span>
                </div>
                {entry.details && (
                  <p className="mt-1 text-xs text-gray-500">{entry.details}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
