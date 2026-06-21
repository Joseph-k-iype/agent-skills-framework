import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Package, Search, Grid3X3, List } from 'lucide-react'
import { api } from '../lib/api'
import { shortHash, pluralize } from '../lib/utils'

export default function SkillCatalog() {
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const [view, setView] = useState<'grid' | 'list'>('grid')

  // Keep the input synced with the URL ?q=, so a repeat search from the TopBar
  // while already on this page actually updates results (previously the initial
  // value was read only once and later searches were ignored).
  useEffect(() => {
    setQuery(searchParams.get('q') ?? '')
  }, [searchParams])

  const { data: skills, isLoading } = useQuery({
    queryKey: ['skills'],
    queryFn: api.skills.list,
  })

  const entries = Object.entries(skills ?? {})

  const filtered = entries.filter(([name]) =>
    !query || name.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Catalog</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Skill Catalog</h2>
          <p className="mt-2 text-sm text-ink-2">
            {isLoading ? 'Loading...' : `${pluralize(entries.length, 'skill')} available`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setView('grid')}
            className={`btn-ghost p-2 ${view === 'grid' ? 'text-accent-500' : 'text-ink-3'}`}
          >
            <Grid3X3 size={16} />
          </button>
          <button
            onClick={() => setView('list')}
            className={`btn-ghost p-2 ${view === 'list' ? 'text-accent-500' : 'text-ink-3'}`}
          >
            <List size={16} />
          </button>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
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
          <Package size={48} className="mx-auto text-ink-3" />
          <p className="mt-4 text-lg font-medium text-ink-2">No skills found</p>
          <p className="mt-1 text-sm text-ink-3">
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
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2 transition group-hover:text-ink">
                    <Package size={20} />
                  </div>
                  {skillId && (
                    <span className="font-mono text-xs text-ink-3">
                      {shortHash(skillId)}
                    </span>
                  )}
                </div>
                <h3 className="mt-3 text-sm font-semibold text-ink transition group-hover:text-ink">
                  {name}
                </h3>
                <p className="mt-1 text-xs text-ink-3">
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
                className="card-hover group flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2 transition group-hover:text-ink">
                    <Package size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-ink">{name}</p>
                    <p className="text-xs text-ink-3">
                      v{info.latest} · {pluralize(info.versions?.length ?? 1, 'version')}
                    </p>
                  </div>
                </div>
                {skillId && (
                  <span className="font-mono text-xs text-ink-3">{shortHash(skillId)}</span>
                )}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
