import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { TopNavLayout, SidebarLayout } from "@/app/layouts/SidebarLayout";
import { useAuthStore, type Role } from "@/stores/authStore";

/** Gate that requires a session and renders the role-appropriate shell. */
export function RequireAuth() {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.accessToken);

  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  // Consumer gets the top-nav marketplace shell; developer/admin get the sidebar.
  return user.role === "consumer" ? <TopNavLayout /> : <SidebarLayout />;
}

/** Route-level role gate (UX only — the API is the real authority). */
export function RequireRole({ allow, children }: { allow: Role[]; children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  if (!allow.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
