import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Database,
  Package,
  GitBranch,
  Plus,
  RefreshCw,
  Folder,
  AlertCircle,
} from 'lucide-react'
import { api } from '../lib/api'
import { RequirePermission } from '../components/RequireRole'

export default function Registry() {
  const queryClient = useQueryClient()
  const [showAddSource, setShowAddSource] = useState(false)
  const [sourceType, setSourceType] = useState<'local' | 'git'>('git')
  const [sourceUrl, setSourceUrl] = useState('')
  const [sourcePath, setSourcePath] = useState('')
  const [sourceRef, setSourceRef] = useState('main')

  const { data: info, isLoading: infoLoading } = useQuery({
    queryKey: ['registry-info'],
    queryFn: api.registry.info,
  })

  const { data: sources, isLoading: sourcesLoading } = useQuery({
    queryKey: ['registry-sources'],
    queryFn: api.registry.sources,
  })

  const syncMutation = useMutation({
    mutationFn: api.registry.sync,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registry-info'] })
      queryClient.invalidateQueries({ queryKey: ['registry-sources'] })
      queryClient.invalidateQueries({ queryKey: ['skills'] })
    },
  })

  const addSourceMutation = useMutation({
    mutationFn: (config: { type: string; url?: string; path?: string; ref: string }) =>
      api.registry.addSource(config as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registry-sources'] })
      queryClient.invalidateQueries({ queryKey: ['registry-info'] })
      setShowAddSource(false)
      setSourceUrl('')
      setSourcePath('')
      setSourceRef('main')
    },
  })

  const handleAddSource = (e: React.FormEvent) => {
    e.preventDefault()
    addSourceMutation.mutate({
      type: sourceType,
      url: sourceType === 'git' ? sourceUrl : undefined,
      path: sourceType === 'local' ? sourcePath : undefined,
      ref: sourceRef,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Overview</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Registry</h2>
          <p className="mt-2 text-sm text-ink-2">
            Manage skill registry and sources
          </p>
        </div>
        <RequirePermission actions={['registry:manage']}>
          <div className="flex gap-3">
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="btn-secondary"
            >
              <RefreshCw size={16} className={syncMutation.isPending ? 'animate-spin' : ''} />
              Sync
            </button>
            <button onClick={() => setShowAddSource(!showAddSource)} className="btn-primary">
              <Plus size={16} />
              Add Source
            </button>
          </div>
        </RequirePermission>
      </div>

      {showAddSource && (
        <RequirePermission actions={['registry:manage']}>
        <div className="card">
          <h3 className="eyebrow mb-4">
            Add Registry Source
          </h3>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setSourceType('git')}
                className={`btn-ghost flex-1 ${sourceType === 'git' ? 'text-accent-500 bg-canvas' : ''}`}
              >
                <GitBranch size={16} /> Git Repository
              </button>
              <button
                type="button"
                onClick={() => setSourceType('local')}
                className={`btn-ghost flex-1 ${sourceType === 'local' ? 'text-accent-500 bg-canvas' : ''}`}
              >
                <Folder size={16} /> Local Directory
              </button>
            </div>
            {sourceType === 'git' ? (
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="Repository URL"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  className="input flex-1"
                  required
                />
                <input
                  type="text"
                  placeholder="Ref (main)"
                  value={sourceRef}
                  onChange={(e) => setSourceRef(e.target.value)}
                  className="input w-32"
                />
              </div>
            ) : (
              <input
                type="text"
                placeholder="Local path"
                value={sourcePath}
                onChange={(e) => setSourcePath(e.target.value)}
                className="input"
                required
              />
            )}
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowAddSource(false)} className="btn-ghost">
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={addSourceMutation.isPending}>
                {addSourceMutation.isPending ? 'Adding...' : 'Add Source'}
              </button>
            </div>
            {addSourceMutation.isError && (
              <p className="flex items-center gap-1.5 text-sm text-ink-2">
                <span className="h-1.5 w-1.5 rounded-full bg-bad" /> Failed to add source
              </p>
            )}
            {addSourceMutation.isSuccess && (
              <p className="flex items-center gap-1.5 text-sm text-ink-2">
                <span className="h-1.5 w-1.5 rounded-full bg-ok" /> Source added successfully
              </p>
            )}
          </form>
        </div>
        </RequirePermission>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Schema Version', value: info?.schema_version ?? '...', icon: Database },
          { label: 'Skills', value: info?.skill_count ?? '...', icon: Package },
          { label: 'Sources', value: info?.sources?.length ?? '...', icon: GitBranch },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="card">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
                <Icon size={20} />
              </div>
              <div>
                <p className="eyebrow">{label}</p>
                <p className="mt-1 text-2xl font-light tabular-nums tracking-tightish text-ink">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <section>
        <h3 className="eyebrow mb-4">Registry Sources</h3>
        <div className="card p-0">
          {sourcesLoading ? (
            <div className="divide-y divide-line">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="h-16 animate-pulse bg-canvas" />
              ))}
            </div>
          ) : !sources?.length ? (
            <div className="px-5 py-12 text-center">
              <Database size={28} className="mx-auto text-ink-3" />
              <p className="mt-3 text-sm text-ink-2">No sources configured</p>
            </div>
          ) : (
            <div className="divide-y divide-line">
              {sources.map((source, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
                      {source.type === 'git' ? <GitBranch size={14} /> : <Folder size={14} />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink capitalize">{source.type} source</p>
                      <p className="font-mono text-xs text-ink-3">
                        {source.url || source.path || 'No path specified'}
                        {source.ref && ` @ ${source.ref}`}
                      </p>
                    </div>
                  </div>
                  <span className="tag">{source.type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {syncMutation.data && (
        <div className="card">
          <p className="flex items-center gap-1.5 text-sm text-ink">
            <span className={`h-1.5 w-1.5 rounded-full ${syncMutation.data.errors?.length ? 'bg-warn' : 'bg-ok'}`} />
            Synced {syncMutation.data.synced} {syncMutation.data.synced === 1 ? 'skill' : 'skills'} from{' '}
            {sources?.length ?? 0} {(sources?.length ?? 0) === 1 ? 'source' : 'sources'}
          </p>
          {syncMutation.data.errors?.map((err, i) => (
            <p key={i} className="mt-1 flex items-center gap-1.5 text-xs text-ink-2">
              <AlertCircle size={12} className="text-ink-3" /> {err}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
