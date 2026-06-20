import { ReactNode } from 'react'
import { useAuth, UserRole } from '../lib/auth'

interface RequireRoleProps {
  roles: UserRole[]
  fallback?: ReactNode
  children: ReactNode
}

interface RequirePermissionProps {
  actions: string[]
  fallback?: ReactNode
  children: ReactNode
}

export function RequireRole({ roles, fallback = null, children }: RequireRoleProps) {
  const { isAtLeast } = useAuth()
  const allowed = roles.some((r) => isAtLeast(r))
  return allowed ? <>{children}</> : <>{fallback}</>
}

export function RequirePermission({ actions, fallback = null, children }: RequirePermissionProps) {
  const { can } = useAuth()
  return can(...actions) ? <>{children}</> : <>{fallback}</>
}
