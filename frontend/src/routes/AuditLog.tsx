import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Clock, CheckCircle2, XCircle, Info } from 'lucide-react'
import { api } from '../lib/api'
import ErrorState from '../components/ErrorState'
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

  const { data, isLoading, isError, error, refetch } = useQuery({
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
    <div className="space-y-10">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Activity</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Audit Log</h2>
          <p className="mt-2 text-sm text-ink-2">Track skill operations and changes</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`btn-ghost text-xs ${filter === f.key ? 'bg-canvas text-ink' : ''}`}
          >
            {f.label}
            <span className="ml-1.5 text-ink-3">({f.count})</span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded bg-canvas" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState error={error} onRetry={refetch} title="Couldn't load audit log" />
      ) : auditLog.length === 0 ? (
        <div className="card py-16 text-center">
          <Clock size={48} className="mx-auto text-ink-3" />
          <p className="mt-4 text-lg font-medium text-ink-2">No audit entries</p>
          <p className="mt-1 text-sm text-ink-3">
            Publish, install, or sync skills to see activity here
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card py-16 text-center">
          <Clock size={48} className="mx-auto text-ink-3" />
          <p className="mt-4 text-lg font-medium text-ink-2">No matching events</p>
          <p className="mt-1 text-sm text-ink-3">
            No entries match this filter. Try “All Events”.
          </p>
        </div>
      ) : (
        <div className="card p-0">
          <div className="divide-y divide-line">
            {filtered.map((entry) => (
              <div key={entry.id} className="flex items-start gap-4 px-5 py-3.5 transition hover:bg-canvas">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-canvas text-ink-2">
                  {entry.status === 'success' ? <CheckCircle2 size={14} /> :
                   entry.status === 'error' ? <XCircle size={14} /> :
                   <Info size={14} />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        entry.status === 'success' ? 'bg-ok' :
                        entry.status === 'error' ? 'bg-bad' :
                        'bg-ink-3'
                      }`} />
                      <p className="text-sm font-medium text-ink">{entry.action}</p>
                      {entry.skillName && (
                        <span className="badge bg-canvas border border-line text-ink-2">{entry.skillName}</span>
                      )}
                      {entry.version && <span className="font-mono text-xs text-ink-3">v{entry.version}</span>}
                    </div>
                    <span className="shrink-0 font-mono text-xs text-ink-3" title={entry.timestamp}>
                      {relativeTime(entry.timestamp)}
                    </span>
                  </div>
                  {entry.details && <p className="mt-1 text-xs text-ink-3 break-words">{entry.details}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
