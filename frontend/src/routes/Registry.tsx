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
          <h2 className="text-2xl font-bold text-gray-100">Registry</h2>
          <p className="mt-1 text-sm text-gray-400">
            Manage skill registry and sources
          </p>
        </div>
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
      </div>

      {showAddSource && (
        <div className="card border-brand-600/30">
          <h3 className="mb-4 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Add Registry Source
          </h3>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setSourceType('git')}
                className={`btn-ghost flex-1 ${sourceType === 'git' ? 'text-brand-400 bg-brand-600/10' : ''}`}
              >
                <GitBranch size={16} /> Git Repository
              </button>
              <button
                type="button"
                onClick={() => setSourceType('local')}
                className={`btn-ghost flex-1 ${sourceType === 'local' ? 'text-brand-400 bg-brand-600/10' : ''}`}
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
              <p className="text-sm text-red-400">Failed to add source</p>
            )}
            {addSourceMutation.isSuccess && (
              <p className="text-sm text-emerald-400">Source added successfully</p>
            )}
          </form>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Schema Version', value: info?.schema_version ?? '...', icon: Database, color: 'text-brand-400 bg-brand-600/10' },
          { label: 'Skills', value: info?.skill_count ?? '...', icon: Package, color: 'text-emerald-400 bg-emerald-600/10' },
          { label: 'Sources', value: info?.sources?.length ?? '...', icon: GitBranch, color: 'text-amber-400 bg-amber-600/10' },
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

      <div className="card">
        <h3 className="mb-4 text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Registry Sources
        </h3>
        {sourcesLoading ? (
          <div className="space-y-2">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded bg-gray-800" />
            ))}
          </div>
        ) : !sources?.length ? (
          <div className="py-8 text-center">
            <Database size={32} className="mx-auto text-gray-600" />
            <p className="mt-2 text-sm text-gray-500">No sources configured</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sources.map((source, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900/50 p-3">
                <div className="flex items-center gap-3">
                  <div className={`flex h-8 w-8 items-center justify-center rounded ${
                    source.type === 'git' ? 'bg-amber-600/20 text-amber-400' : 'bg-brand-600/20 text-brand-400'
                  }`}>
                    {source.type === 'git' ? <GitBranch size={14} /> : <Folder size={14} />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-200 capitalize">{source.type} source</p>
                    <p className="text-xs text-gray-500">
                      {source.url || source.path || 'No path specified'}
                      {source.ref && ` @ ${source.ref}`}
                    </p>
                  </div>
                </div>
                <span className={`badge ${
                  source.type === 'git' ? 'bg-amber-600/10 text-amber-400' : 'bg-brand-600/10 text-brand-400'
                }`}>
                  {source.type}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {syncMutation.data && (
        <div className={`card ${syncMutation.data.errors?.length ? 'border-amber-600/30' : 'border-emerald-600/30'}`}>
          <p className={`text-sm ${syncMutation.data.errors?.length ? 'text-amber-400' : 'text-emerald-400'}`}>
            Synced {syncMutation.data.synced} {syncMutation.data.synced === 1 ? 'skill' : 'skills'} from{' '}
            {sources?.length ?? 0} {(sources?.length ?? 0) === 1 ? 'source' : 'sources'}
          </p>
          {syncMutation.data.errors?.map((err, i) => (
            <p key={i} className="mt-1 flex items-center gap-1.5 text-xs text-amber-400">
              <AlertCircle size={12} /> {err}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
