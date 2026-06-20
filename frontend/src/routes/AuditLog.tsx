import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Clock, CheckCircle2, XCircle, Info } from 'lucide-react'
import { api } from '../lib/api'
import type { AuditEntry } from '../lib/types'

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const sec = Math.round((Date.now() - then) / 1000)
  if (sec < 60) return `${sec}s ago`
  const min = Math.round(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.round(min / 60)
  if (hr < 24) return `${hr}h ago`
  const day = Math.round(hr / 24)
  if (day < 30) return `${day}d ago`
  return new Date(iso).toLocaleDateString()
}

export default function AuditLog() {
  const [filter, setFilter] = useState<string>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['audit'],
    queryFn: () => api.audit.list(500),
  })

  const auditLog: AuditEntry[] = data?.entries ?? []

  const filtered =
    filter === 'all'
      ? auditLog
      : filter === 'errors'
        ? auditLog.filter((e) => e.status === 'error')
        : auditLog.filter((e) => e.action.toLowerCase().includes(filter))

  const filters = [
    { key: 'all', label: 'All Events', count: auditLog.length },
    { key: 'publish', label: 'Publishes', count: auditLog.filter((e) => e.action.toLowerCase().includes('publish')).length },
    { key: 'install', label: 'Installs', count: auditLog.filter((e) => e.action.toLowerCase().includes('install')).length },
    { key: 'errors', label: 'Errors', count: auditLog.filter((e) => e.status === 'error').length },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Audit Log</h2>
          <p className="mt-1 text-sm text-gray-400">Track skill operations and changes</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
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

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded bg-gray-800" />
          ))}
        </div>
      ) : auditLog.length === 0 ? (
        <div className="card py-16 text-center">
          <Clock size={48} className="mx-auto text-gray-700" />
          <p className="mt-4 text-lg font-medium text-gray-400">No audit entries</p>
          <p className="mt-1 text-sm text-gray-500">
            Publish, install, or sync skills to see activity here
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
                {i < filtered.length - 1 && <div className="mt-1 w-px flex-1 bg-gray-800" />}
              </div>
              <div className="flex-1 pb-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-gray-200">{entry.action}</p>
                    {entry.skillName && (
                      <span className="badge bg-brand-600/10 text-brand-400">{entry.skillName}</span>
                    )}
                    {entry.version && <span className="text-xs text-gray-500">v{entry.version}</span>}
                  </div>
                  <span className="shrink-0 text-xs text-gray-600" title={entry.timestamp}>
                    {relativeTime(entry.timestamp)}
                  </span>
                </div>
                {entry.details && <p className="mt-1 text-xs text-gray-500 break-words">{entry.details}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
