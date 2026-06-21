import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './routes/Dashboard'
import { AuthProvider } from './lib/auth'

const SkillCatalog = lazy(() => import('./routes/SkillCatalog'))
const SkillDetail = lazy(() => import('./routes/SkillDetail'))
const CreateSkill = lazy(() => import('./routes/CreateSkill'))
const Registry = lazy(() => import('./routes/Registry'))
const KnowledgeGraph = lazy(() => import('./routes/KnowledgeGraph'))
const Governance = lazy(() => import('./routes/Governance'))
const Deployments = lazy(() => import('./routes/Deployments'))
const AuditLog = lazy(() => import('./routes/AuditLog'))
const Settings = lazy(() => import('./routes/Settings'))
const NotFound = lazy(() => import('./routes/NotFound'))

function PageLoader() {
  return (
    <div className="space-y-4 p-6">
      <div className="h-8 w-48 animate-pulse rounded bg-canvas" />
      <div className="h-64 animate-pulse rounded-xl bg-canvas" />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell>
        <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/skills" element={<SkillCatalog />} />
              <Route path="/skills/new" element={<CreateSkill />} />
              <Route path="/skills/:name" element={<SkillDetail />} />
              <Route path="/registry" element={<Registry />} />
              <Route path="/graph" element={<KnowledgeGraph />} />
              <Route path="/governance" element={<Governance />} />
              <Route path="/deployments" element={<Deployments />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </AppShell>
    </AuthProvider>
  )
}
