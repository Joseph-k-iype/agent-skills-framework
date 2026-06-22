import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Package, Database, Plus, Search, ArrowUpRight } from 'lucide-react'
import { api } from '../lib/api'
import { pluralize, shortHash } from '../lib/utils'
import ErrorState from '../components/ErrorState'

export default function Dashboard() {
  const { data: stats, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: api.dashboard.stats,
  })

  const recentSkills = stats?.latest_skills
    ? Object.entries(stats.latest_skills)
        .sort(([, a], [, b]) => (b.versions?.length ?? 0) - (a.versions?.length ?? 0))
        .slice(0, 5)
    : []

  // On error, show "—" rather than a misleading "0" (which reads as "registry empty").
  const pending = isLoading || isError
  const metrics = [
    {
      label: 'Total Skills',
      value: pending ? '—' : stats?.total_skills ?? 0,
      headline: true,
    },
    { label: 'Versions', value: pending ? '—' : stats?.total_versions ?? 0 },
    { label: 'Sources', value: pending ? '—' : stats?.sources_count ?? 0 },
    { label: 'Registry', value: isLoading ? '—' : isError ? 'Offline' : 'Active' },
  ]

  return (
    <div className="space-y-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <p className="eyebrow">Overview</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Dashboard</h2>
          <p className="mt-2 text-sm text-ink-2">The state of your Agent Skills Framework.</p>
        </div>
        <div className="flex gap-3">
          <Link to="/skills" className="btn-secondary">
            <Search size={16} />
            Browse Skills
          </Link>
          <Link to="/skills/new" className="btn-primary">
            <Plus size={16} />
            New Skill
          </Link>
        </div>
      </div>

      {/* Metrics — monochrome, big numerals, red reserved for the headline figure */}
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line lg:grid-cols-4">
        {metrics.map(({ label, value, headline }) => (
          <div key={label} className="bg-surface px-5 py-6">
            <p className="eyebrow">{label}</p>
            <p
              className={`mt-3 text-4xl font-light tabular-nums tracking-tightish ${
                headline ? 'text-accent-500' : 'text-ink'
              }`}
            >
              {value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="eyebrow">Recent Skills</h3>
            <Link
              to="/skills"
              className="inline-flex items-center gap-1 text-xs font-medium text-ink-2 transition hover:text-ink"
            >
              View all <ArrowUpRight size={13} />
            </Link>
          </div>
          <div className="card p-0">
            {isLoading ? (
              <div className="divide-y divide-line">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-[60px] animate-pulse bg-canvas" />
                ))}
              </div>
            ) : isError ? (
              <ErrorState error={error} onRetry={refetch} title="Couldn't load registry stats" />
            ) : recentSkills.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <Package size={28} className="mx-auto text-ink-3" />
                <p className="mt-3 text-sm text-ink-2">No skills published yet</p>
              </div>
            ) : (
              <div className="divide-y divide-line">
                {recentSkills.map(([name, info]) => {
                  const skillId = info.ids?.[info.latest]
                  return (
                    <Link
                      key={name}
                      to={`/skills/${name}`}
                      className="group flex items-center justify-between px-5 py-3.5 transition hover:bg-canvas"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2 transition group-hover:text-ink">
                          <Package size={15} />
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
        </section>

        <section>
          <h3 className="eyebrow mb-4">Quick Actions</h3>
          <div className="card space-y-1 p-2">
            {[
              {
                to: '/skills/new',
                title: 'Create a Skill',
                desc: 'Scaffold a new skill project',
                icon: Plus,
              },
              {
                to: '/skills',
                title: 'Browse Catalog',
                desc: 'Discover and install skills',
                icon: Search,
              },
              {
                to: '/graph',
                title: 'Knowledge Graph',
                desc: 'Explore skill dependencies',
                icon: Database,
              },
            ].map(({ to, title, desc, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="group flex items-center gap-4 rounded-lg px-3 py-3 transition hover:bg-canvas"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-surface text-ink-2 transition group-hover:border-accent-200 group-hover:text-accent-500">
                  <Icon size={17} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-ink">{title}</p>
                  <p className="text-xs text-ink-3">{desc}</p>
                </div>
                <ArrowUpRight
                  size={15}
                  className="text-ink-3 opacity-0 transition group-hover:opacity-100"
                />
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
