import { useLocation, useNavigate } from 'react-router-dom'
import { Search, Plus, UserCog } from 'lucide-react'
import { useState } from 'react'
import { RequirePermission } from '../RequireRole'
import { useAuth, roleOptions } from '../../lib/auth'

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/skills': 'Skills',
  '/registry': 'Registry',
  '/graph': 'Knowledge Graph',
  '/governance': 'Governance',
  '/deployments': 'Deployments',
  '/audit': 'Audit Log',
  '/settings': 'Settings',
}

export default function TopBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { role, setRole } = useAuth()
  const [search, setSearch] = useState('')

  const baseRoute = '/' + (location.pathname.split('/')[1] || '')
  const label = routeLabels[location.pathname] || routeLabels[baseRoute] || 'Skill Detail'

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (search.trim()) {
      navigate(`/skills?q=${encodeURIComponent(search.trim())}`)
    }
  }

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b border-line bg-surface/80 px-8 backdrop-blur-md">
      <h1 className="text-lg font-semibold tracking-tightish text-ink">{label}</h1>

      <div className="flex-1" />

      <form onSubmit={handleSearch} className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
        <input
          type="text"
          placeholder="Search skills..."
          aria-label="Search skills"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input w-72 rounded-full pl-9"
        />
      </form>

      {/* Always-available role preview switcher (client-side only — not an authz
          boundary). Keeps the role selector reachable even when Settings is gated. */}
      <label className="relative flex items-center" title="Preview as role">
        <UserCog size={15} className="pointer-events-none absolute left-2.5 text-ink-3" />
        <span className="sr-only">Preview as role</span>
        <select
          aria-label="Preview as role"
          value={role}
          onChange={(e) => setRole(e.target.value as typeof role)}
          className="input cursor-pointer appearance-none rounded-full py-1.5 pl-8 pr-3 text-xs"
        >
          {roleOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>

      <RequirePermission actions={['skill:create']}>
        <button onClick={() => navigate('/skills/new')} className="btn-primary">
          <Plus size={16} />
          New Skill
        </button>
      </RequirePermission>
    </header>
  )
}
