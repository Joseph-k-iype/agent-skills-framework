import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

export type UserRole = 'admin' | 'developer' | 'consumer' | 'governance' | 'viewer'

const ROLE_STORAGE_KEY = 'skills.role'

interface AuthState {
  role: UserRole
  setRole: (role: UserRole) => void
  can: (...actions: string[]) => boolean
  isAtLeast: (minRole: UserRole) => boolean
}

const roleHierarchy: Record<UserRole, number> = {
  viewer: 0,
  consumer: 1,
  developer: 2,
  governance: 3,
  admin: 4,
}

const rolePermissions: Record<UserRole, string[]> = {
  admin: ['*'],
  developer: ['skill:create', 'skill:edit', 'skill:delete', 'skill:publish', 'skill:validate', 'skill:verify', 'skill:evaluate', 'registry:manage'],
  consumer: ['skill:install', 'skill:view', 'skill:search'],
  governance: ['skill:validate', 'skill:verify', 'skill:view', 'skill:audit'],
  viewer: ['skill:view', 'skill:search'],
}

const AuthContext = createContext<AuthState | null>(null)

function loadRole(): UserRole {
  if (typeof localStorage === 'undefined') return 'developer'
  const saved = localStorage.getItem(ROLE_STORAGE_KEY)
  return saved && saved in roleHierarchy ? (saved as UserRole) : 'developer'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<UserRole>(loadRole)

  const setRole = useCallback((next: UserRole) => {
    setRoleState(next)
    try {
      localStorage.setItem(ROLE_STORAGE_KEY, next)
    } catch {
      // Persistence is best-effort (e.g. storage disabled); ignore.
    }
  }, [])

  const can = useCallback(
    (...actions: string[]) => {
      if (role === 'admin') return true
      const perms = rolePermissions[role]
      return actions.some((a) => perms.includes(a))
    },
    [role],
  )

  const isAtLeast = useCallback(
    (minRole: UserRole) => roleHierarchy[role] >= roleHierarchy[minRole],
    [role],
  )

  return (
    <AuthContext.Provider value={{ role, setRole, can, isAtLeast }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export const roleOptions: { value: UserRole; label: string; description: string }[] = [
  { value: 'admin', label: 'Admin', description: 'Full access to all features' },
  { value: 'developer', label: 'Developer', description: 'Create, publish, and manage skills' },
  { value: 'consumer', label: 'Consumer', description: 'Browse, search, and install skills' },
  { value: 'governance', label: 'Governance', description: 'Validate, audit, and enforce policies' },
  { value: 'viewer', label: 'Viewer', description: 'Read-only access' },
]
