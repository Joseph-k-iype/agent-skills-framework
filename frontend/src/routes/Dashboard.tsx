import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Package, GitBranch, Database, Layers, Plus, Search } from 'lucide-react'
import { api } from '../lib/api'
import { pluralize, shortHash } from '../lib/utils'

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: api.dashboard.stats,
  })

  const recentSkills = stats?.latest_skills
    ? Object.entries(stats.latest_skills)
        .sort(([, a], [, b]) => (b.versions?.length ?? 0) - (a.versions?.length ?? 0))
        .slice(0, 5)
    : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Dashboard</h2>
          <p className="mt-1 text-sm text-gray-400">
            Overview of the Agent Skills Framework
          </p>
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: 'Total Skills',
            value: isLoading ? '...' : stats?.total_skills ?? 0,
            icon: Package,
            color: 'text-brand-400 bg-brand-600/10',
          },
          {
            label: 'Versions',
            value: isLoading ? '...' : stats?.total_versions ?? 0,
            icon: Layers,
            color: 'text-emerald-400 bg-emerald-600/10',
          },
          {
            label: 'Sources',
            value: isLoading ? '...' : stats?.sources_count ?? 0,
            icon: Database,
            color: 'text-amber-400 bg-amber-600/10',
          },
          {
            label: 'Registry',
            value: isLoading ? '...' : 'Active',
            icon: GitBranch,
            color: 'text-rose-400 bg-rose-600/10',
          },
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

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-4 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Recent Skills
          </h3>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-12 animate-pulse rounded bg-gray-800" />
              ))}
            </div>
          ) : recentSkills.length === 0 ? (
            <div className="py-8 text-center">
              <Package size={32} className="mx-auto text-gray-600" />
              <p className="mt-2 text-sm text-gray-500">No skills published yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentSkills.map(([name, info]) => {
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
                      <span className="text-xs text-gray-600 font-mono">
                        {shortHash(skillId)}
                      </span>
                    )}
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="mb-4 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Quick Actions
          </h3>
          <div className="space-y-3">
            <Link
              to="/skills/new"
              className="card-hover flex items-center gap-4"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600/10 text-brand-400">
                <Plus size={20} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-200">Create a Skill</p>
                <p className="text-xs text-gray-500">Scaffold a new skill project</p>
              </div>
            </Link>
            <Link
              to="/skills"
              className="card-hover flex items-center gap-4"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600/10 text-emerald-400">
                <Search size={20} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-200">Browse Catalog</p>
                <p className="text-xs text-gray-500">Discover and install skills</p>
              </div>
            </Link>
            <Link
              to="/graph"
              className="card-hover flex items-center gap-4"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-600/10 text-amber-400">
                <Database size={20} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-200">Knowledge Graph</p>
                <p className="text-xs text-gray-500">Explore skill dependencies</p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
