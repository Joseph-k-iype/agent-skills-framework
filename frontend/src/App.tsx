import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import Dashboard from './routes/Dashboard'
import SkillCatalog from './routes/SkillCatalog'
import SkillDetail from './routes/SkillDetail'
import CreateSkill from './routes/CreateSkill'
import Registry from './routes/Registry'
import KnowledgeGraph from './routes/KnowledgeGraph'
import Governance from './routes/Governance'
import Deployments from './routes/Deployments'
import AuditLog from './routes/AuditLog'
import Settings from './routes/Settings'
import { AuthProvider } from './lib/auth'

export default function App() {
  return (
    <AuthProvider>
      <AppShell>
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
        </Routes>
      </AppShell>
    </AuthProvider>
  )
}
