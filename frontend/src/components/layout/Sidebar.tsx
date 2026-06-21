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
    <aside className="flex w-64 flex-col border-r border-gray-800 bg-gray-950">
      <div className="flex h-16 items-center gap-3 border-b border-gray-800 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
          <Package size={18} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-100">Agent Skills</p>
          <p className="text-xs text-gray-500">Framework</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems
          .filter((item) => !item.minRole || isAtLeast(item.minRole))
          .map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'bg-brand-600/10 text-brand-400'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`
            }
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-800 px-6 py-4">
        <p className="text-xs text-gray-600">v0.1.0</p>
      </div>
    </aside>
  )
}
