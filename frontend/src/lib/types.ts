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
  status: 'active' | 'inactive' | 'error'
  skillCount: number
  lastSync?: string
  url?: string
  path?: string
}

export interface GovernancePolicy {
  id: string
  name: string
  description: string
  status: 'pass' | 'fail' | 'warn' | 'unknown'
  category: string
  skillCount: number
  passingCount: number
}
