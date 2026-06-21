import { useLocation, useNavigate } from 'react-router-dom'
import { Search, Plus } from 'lucide-react'
import { useState } from 'react'
import { RequirePermission } from '../RequireRole'

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
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input w-72 rounded-full pl-9"
        />
      </form>

      <RequirePermission actions={['skill:create']}>
        <button onClick={() => navigate('/skills/new')} className="btn-primary">
          <Plus size={16} />
          New Skill
        </button>
      </RequirePermission>
    </header>
  )
}
