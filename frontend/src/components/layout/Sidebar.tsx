import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Package,
  Database,
  Network,
  Shield,
  Settings,
  GitBranch,
  ClipboardList,
} from 'lucide-react'
import { useAuth, UserRole } from '../../lib/auth'

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  minRole?: UserRole
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/skills', label: 'Skills', icon: Package },
  { to: '/registry', label: 'Registry', icon: Database, minRole: 'consumer' },
  { to: '/graph', label: 'Knowledge Graph', icon: Network },
  { to: '/governance', label: 'Governance', icon: Shield, minRole: 'governance' },
  { to: '/deployments', label: 'Deployments', icon: GitBranch },
  { to: '/audit', label: 'Audit Log', icon: ClipboardList, minRole: 'governance' },
  { to: '/settings', label: 'Settings', icon: Settings, minRole: 'admin' },
]

export default function Sidebar() {
  const { isAtLeast } = useAuth()
  return (
    <aside className="flex w-64 flex-col border-r border-line bg-surface">
      <div className="flex h-16 items-center gap-3 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink">
          <Package size={17} className="text-surface" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tightish text-ink">Agent Skills</p>
          <p className="eyebrow">Framework</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-5">
        {navItems
          .filter((item) => !item.minRole || isAtLeast(item.minRole))
          .map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-canvas text-ink'
                    : 'text-ink-2 hover:bg-canvas hover:text-ink'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`absolute left-0 top-1/2 h-5 -translate-y-1/2 rounded-full bg-accent-500 transition-all ${
                      isActive ? 'w-1 opacity-100' : 'w-1 opacity-0'
                    }`}
                  />
                  <item.icon
                    size={18}
                    className={isActive ? 'text-ink' : 'text-ink-3 group-hover:text-ink'}
                  />
                  {item.label}
                </>
              )}
            </NavLink>
          ))}
      </nav>

      <div className="px-6 py-4">
        <p className="font-mono text-xs text-ink-3">v0.1.0</p>
      </div>
    </aside>
  )
}
