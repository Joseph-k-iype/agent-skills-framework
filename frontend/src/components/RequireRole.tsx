import { ReactNode } from 'react'
import { ShieldAlert } from 'lucide-react'
import { useAuth, UserRole, roleOptions } from '../lib/auth'

interface RequireRoleProps {
  /** The user's role must be exactly one of these. */
  roles: UserRole[]
  fallback?: ReactNode
  children: ReactNode
}

interface RequireMinRoleProps {
  /** The user's role must rank at or above this in the hierarchy. */
  minRole: UserRole
  fallback?: ReactNode
  children: ReactNode
}

interface RequirePermissionProps {
  actions: string[]
  fallback?: ReactNode
  children: ReactNode
}

/** True membership check: the active role must be one of `roles`. */
export function RequireRole({ roles, fallback = null, children }: RequireRoleProps) {
  const { role } = useAuth()
  return roles.includes(role) ? <>{children}</> : <>{fallback}</>
}

/** Hierarchy check: the active role must rank at or above `minRole`. */
export function RequireMinRole({ minRole, fallback = null, children }: RequireMinRoleProps) {
  const { isAtLeast } = useAuth()
  return isAtLeast(minRole) ? <>{children}</> : <>{fallback}</>
}

export function RequirePermission({ actions, fallback = null, children }: RequirePermissionProps) {
  const { can } = useAuth()
  return can(...actions) ? <>{children}</> : <>{fallback}</>
}

/**
 * Route-level guard: renders a "permission denied" page (not a security
 * boundary — real authz is server-side) so a gated page reached by direct URL
 * matches the sidebar's visibility instead of silently rendering.
 */
export function RoleGate({ minRole, children }: { minRole: UserRole; children: ReactNode }) {
  const label = roleOptions.find((r) => r.value === minRole)?.label ?? minRole
  return (
    <RequireMinRole
      minRole={minRole}
      fallback={
        <div className="card mx-auto mt-10 max-w-lg text-center">
          <ShieldAlert size={40} className="mx-auto text-ink-3" />
          <h2 className="mt-4 text-lg font-semibold text-ink">Access restricted</h2>
          <p className="mt-1 text-sm text-ink-2">
            This page requires the <strong>{label}</strong> role or higher. Switch roles in
            Settings to preview it.
          </p>
        </div>
      }
    >
      {children}
    </RequireMinRole>
  )
}
