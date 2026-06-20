import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import { Package, Search, Grid3X3, List } from 'lucide-react'
import { api } from '../lib/api'
import { shortHash, pluralize } from '../lib/utils'

export default function SkillCatalog() {
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') ?? ''
  const [query, setQuery] = useState(initialQuery)
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [runtimeFilter, setRuntimeFilter] = useState<string>('')

  const { data: skills, isLoading } = useQuery({
    queryKey: ['skills'],
    queryFn: api.skills.list,
  })

  const entries = Object.entries(skills ?? {})

  const filtered = entries.filter(([name, info]) => {
    if (query && !name.toLowerCase().includes(query.toLowerCase())) return false
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Skill Catalog</h2>
          <p className="mt-1 text-sm text-gray-400">
            {isLoading ? 'Loading...' : `${pluralize(entries.length, 'skill')} available`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setView('grid')}
            className={`btn-ghost p-2 ${view === 'grid' ? 'text-brand-400' : ''}`}
          >
            <Grid3X3 size={16} />
          </button>
          <button
            onClick={() => setView('list')}
            className={`btn-ghost p-2 ${view === 'list' ? 'text-brand-400' : ''}`}
          >
            <List size={16} />
          </button>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search by name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="input pl-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className={view === 'grid'
          ? 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
          : 'space-y-2'
        }>
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card h-28 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card py-16 text-center">
          <Package size={48} className="mx-auto text-gray-700" />
          <p className="mt-4 text-lg font-medium text-gray-400">No skills found</p>
          <p className="mt-1 text-sm text-gray-500">
            {query ? 'Try a different search term' : 'The registry is empty'}
          </p>
        </div>
      ) : view === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map(([name, info]) => {
            const skillId = info.ids?.[info.latest]
            return (
              <Link key={name} to={`/skills/${name}`} className="card-hover group">
                <div className="flex items-start justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600/10 text-brand-400">
                    <Package size={20} />
                  </div>
                  {skillId && (
                    <span className="text-xs text-gray-700 font-mono">
                      {shortHash(skillId)}
                    </span>
                  )}
                </div>
                <h3 className="mt-3 text-sm font-semibold text-gray-200 group-hover:text-brand-400 transition">
                  {name}
                </h3>
                <p className="mt-1 text-xs text-gray-500">
                  v{info.latest} · {pluralize(info.versions?.length ?? 1, 'version')}
                </p>
              </Link>
            )
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(([name, info]) => {
            const skillId = info.ids?.[info.latest]
            return (
              <Link
                key={name}
                to={`/skills/${name}`}
                className="card-hover flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-brand-600/20 text-brand-400">
                    <Package size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-200">{name}</p>
                    <p className="text-xs text-gray-500">
                      v{info.latest} · {pluralize(info.versions?.length ?? 1, 'version')}
                    </p>
                  </div>
                </div>
                {skillId && (
                  <span className="text-xs text-gray-600 font-mono">{shortHash(skillId)}</span>
                )}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
