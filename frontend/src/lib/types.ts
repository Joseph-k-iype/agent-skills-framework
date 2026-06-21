export interface SkillEntry {
  latest: string
  versions: string[]
  ids: Record<string, string>
  // Only present on the per-skill detail response (GET /api/skills/{name});
  // the list endpoint (GET /api/skills, RegistryClient.list_skills()) omits it.
  locations?: Record<string, string>
}

export interface SkillVersion {
  version: string
  id: string
}

export interface SkillManifest {
  id?: string
  name: string
  version: string
  description?: string
  runtime: 'python' | 'typescript'
  api_version: number
  entry: string
  triggers?: {
    events?: string[]
    commands?: string[]
  }
  capabilities?: string[]
  config?: {
    required?: string[]
    schema?: Record<string, unknown>
  }
  dependencies?: {
    pip?: string[]
    npm?: string[]
    skills?: string[]
  }
  permissions?: Array<{
    resource: string
    actions: string[]
  }>
  lifecycle?: {
    on_install?: string
    on_uninstall?: string
    on_upgrade?: string
  }
}

export interface DashboardStats {
  total_skills: number
  total_versions: number
  sources_count: number
  latest_skills: Record<string, SkillEntry>
}

export interface RegistryInfo {
  schema_version: number
  sources: SourceConfig[]
  skill_count: number
  auto_tag: boolean
  workspace: string
  auth_required: boolean
}

export interface SyncResult {
  synced: number
  skills: string[]
  errors: string[]
}

export interface InstallResult {
  success: boolean
  name: string
  version?: string
  path: string
}

export interface ScaffoldRequest {
  manifest: Partial<SkillManifest> & { name: string }
  files?: Record<string, string>
  publish?: boolean
  force?: boolean
}

export interface ScaffoldResult {
  success: boolean
  name?: string
  path?: string
  published?: { id: string; version: string } | null
  errors?: string[]
  scaffolded?: boolean
}

export interface PermissionDetail {
  resource: string
  actions: string[]
}

export interface ImpactResult {
  downstream: string[]
  count: number
}

export interface ComplianceRow {
  name: string
  latest: string
  runtime: string
  valid: boolean | null
  permissions: number
  permission_details: PermissionDetail[]
  capabilities: number
  errors: string[]
  last_evaluation_score: number | null
}

export interface EvalCaseInput {
  type: 'command' | 'event'
  name: string
  args?: string[]
  kwargs?: Record<string, string>
  payload?: Record<string, unknown>
}

export interface EvalCaseExpect {
  mode: 'exact_match' | 'contains' | 'llm_judged'
  value?: Record<string, unknown> | null
  rubric?: string | null
}

export interface EvalCase {
  id: string
  description?: string
  input: EvalCaseInput
  expect: EvalCaseExpect
}

export interface TestExecutorResult {
  case_id: string
  mode: string
  status: 'passed' | 'failed' | 'error' | 'skipped' | 'pending_judgment'
  actual?: Record<string, unknown>
  detail?: string
  rubric?: string
  score?: number | null
  rationale?: string | null
}

export interface ContentCriticFinding {
  id: string
  severity: 'info' | 'warning' | 'error'
  field: string
  message: string
  suggestion?: string
  signature: string
}

export interface EvaluationReport {
  skill_name: string
  skill_version: string
  run_at: string
  judge_status: 'ok' | 'skipped' | 'error'
  judge_skip_reason: string | null
  structural_errors: string[]
  structural_warnings: string[]
  content_critic: {
    findings: ContentCriticFinding[]
    model: string | null
  }
  test_executor: {
    results: TestExecutorResult[]
    passed: number
    failed: number
    total: number
  }
  overall_score: number | null
  summary: string
}

export interface FeedbackEntry {
  finding_id: string
  finding_signature: string
  finding_text: string
  verdict: 'accepted' | 'dismissed'
  verdict_at: string
  verdict_by: string | null
  run_id: string | null
}

export interface FeedbackResponse {
  skill_name: string
  entries: FeedbackEntry[]
}

export interface DeploymentsResponse {
  targets: DeploymentTarget[]
  total_skills: number
  skills: Array<{ name: string; latest: string }>
  last_sync: string | null
}

export interface SourceConfig {
  type: 'local' | 'git'
  path?: string
  url?: string
  ref?: string
  cache?: string
}

export interface ValidationResult {
  valid: boolean
  errors: string[]
  name: string
}

export interface VerifyResult {
  valid: boolean
  name?: string
  version?: string
  id?: string
  errors?: string[]
}

export interface DocResult {
  doc: string
  format: string
  name: string
}

export interface ManifestResponse {
  manifest: SkillManifest
  body: string
  raw: string
}

export interface GraphQueryResult {
  results: Array<Record<string, unknown>>
}

export interface HubSourceConfig {
  type: string
  url?: string
  path?: string
  ref: string
  cache?: string
}

export interface AuditEntry {
  id: string
  action: string
  skillName: string
  version?: string
  timestamp: string
  status: 'success' | 'error' | 'info'
  details?: string
}

export interface DeploymentTarget {
  name: string
  type: 'local' | 'git' | 'remote'
  status: 'active' | 'inactive' | 'error' | 'configured'
  skillCount: number | null
  lastSync?: string | null
  url?: string
  path?: string
  ref?: string
}
