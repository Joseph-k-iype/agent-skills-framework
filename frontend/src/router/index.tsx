import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Placeholder } from "@/shared/components/Placeholder";
import { RequireAuth, RequireRole } from "./RequireAuth";

const LoginPage = lazy(() => import("@/features/auth/pages/LoginPage"));
const DashboardPage = lazy(() => import("@/features/dashboard/pages/DashboardPage"));
const WorkspacePage = lazy(() => import("@/features/workspace/pages/WorkspacePage"));
const KnowledgeGraphPage = lazy(() => import("@/features/knowledge/pages/KnowledgeGraphPage"));
const SkillsPage = lazy(() => import("@/features/skills/pages/SkillsPage"));
const SkillEditorPage = lazy(() => import("@/features/skills/pages/SkillEditorPage"));

const S = (node: ReactNode) => <Suspense fallback={null}>{node}</Suspense>;

export const router = createBrowserRouter([
  { path: "/login", element: S(<LoginPage />) },
  {
    path: "/",
    element: <RequireAuth />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: S(<DashboardPage />) },
      { path: "workspace", element: S(<WorkspacePage />) },
      { path: "knowledge", element: S(<KnowledgeGraphPage />) },
      { path: "skills", element: S(<SkillsPage />) },
      { path: "skills/:id", element: S(<SkillEditorPage />) },
      { path: "marketplace", element: <Placeholder eyebrow="Marketplace" title="Marketplace" phase="Phase 7" /> },
      {
        path: "admin/users",
        element: (
          <RequireRole allow={["admin"]}>
            <Placeholder eyebrow="Administration" title="Users" phase="a later phase" />
          </RequireRole>
        ),
      },
      {
        path: "admin/roles",
        element: (
          <RequireRole allow={["admin"]}>
            <Placeholder eyebrow="Administration" title="Roles" phase="a later phase" />
          </RequireRole>
        ),
      },
      {
        path: "admin/audit",
        element: (
          <RequireRole allow={["admin"]}>
            <Placeholder eyebrow="Administration" title="Audit Log" phase="a later phase" />
          </RequireRole>
        ),
      },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
]);
