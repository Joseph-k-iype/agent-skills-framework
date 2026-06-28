import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";

const SystemStatusPage = lazy(() => import("@/features/system/SystemStatusPage"));

function withSuspense(node: React.ReactNode) {
  return <Suspense fallback={null}>{node}</Suspense>;
}

/**
 * Router shell. Auth-gated layouts (Consumer/Developer/Admin) are introduced in
 * the auth phase; for now the status page validates end-to-end wiring.
 */
export const router = createBrowserRouter([
  { path: "/status", element: withSuspense(<SystemStatusPage />) },
  { path: "*", element: <Navigate to="/status" replace /> },
]);
