import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { PublicLayout } from "@/app/layouts/PublicLayout";
import { Placeholder } from "@/shared/components/Placeholder";
import { RequireAuth, RequireRole } from "./RequireAuth";

const LoginPage = lazy(() => import("@/features/auth/pages/LoginPage"));
const DashboardPage = lazy(() => import("@/features/dashboard/pages/DashboardPage"));
const WorkspacePage = lazy(() => import("@/features/workspace/pages/WorkspacePage"));
const KnowledgeGraphPage = lazy(() => import("@/features/knowledge/pages/KnowledgeGraphPage"));
const ConceptEditorPage = lazy(() => import("@/features/concepts/pages/ConceptEditorPage"));
const MarketplacePage = lazy(() => import("@/features/marketplace/pages/MarketplacePage"));
const MarketplaceDetailPage = lazy(
  () => import("@/features/marketplace/pages/MarketplaceDetailPage"),
);
const InsightsPage = lazy(() => import("@/features/insights/pages/InsightsPage"));
const ApiKeysPage = lazy(() => import("@/features/settings/pages/ApiKeysPage"));

const S = (node: ReactNode) => <Suspense fallback={null}>{node}</Suspense>;

export const router = createBrowserRouter([
  { path: "/login", element: S(<LoginPage />) },

  // Public marketplace — NO auth (PublicLayout is a pathless layout route)
  {
    element: <PublicLayout />,
    children: [
      { index: true, element: S(<MarketplacePage />) },
      { path: "marketplace", element: S(<MarketplacePage />) },
      { path: "marketplace/:id", element: S(<MarketplaceDetailPage />) },
    ],
  },

  // Authenticated app — RequireAuth is now a PATHLESS layout route; child paths
  // stay absolute-from-root exactly as before (/dashboard, /workspace, ...).
  {
    element: <RequireAuth />,
    children: [
      { path: "dashboard", element: S(<DashboardPage />) },
      { path: "workspace", element: S(<WorkspacePage />) },
      { path: "knowledge", element: S(<KnowledgeGraphPage />) },
      { path: "concepts/:workspaceId/*", element: S(<ConceptEditorPage />) },
      { path: "insights", element: S(<InsightsPage />) },
      { path: "settings/api-keys", element: S(<ApiKeysPage />) },
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

  { path: "*", element: <Navigate to="/" replace /> },
]);
