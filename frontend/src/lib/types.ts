export interface SkillEntry {
  latest: string
  versions: string[]
  ids: Record<string, string>
  locations: Record<string, string>
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

export interface ComplianceRow {
  name: string
  latest: string
  runtime: string
  valid: boolean | null
  permissions: number
  capabilities: number
  errors: string[]
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
