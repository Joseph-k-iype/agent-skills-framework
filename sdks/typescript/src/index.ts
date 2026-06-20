export interface SkillContext {
  config: Record<string, unknown>
  logger?: unknown
  registry?: unknown
  state: Record<string, unknown>
  graph?: unknown
}

export interface SkillEvent {
  name: string
  payload: Record<string, unknown>
  source: string
}

export interface SkillCommand {
  name: string
  args: string[]
  kwargs: Record<string, string>
}

export interface SkillResult {
  status: 'success' | 'failure' | 'error'
  data: Record<string, unknown>
  error?: string
  message: string
}

export interface HealthStatus {
  healthy: boolean
  version: string
  details: Record<string, unknown>
}

export interface Skill {
  name: string
  version: string
  skillId: string
  initialize(ctx: SkillContext): Promise<void>
  handleEvent(event: SkillEvent): Promise<SkillResult>
  handleCommand(command: SkillCommand): Promise<SkillResult>
  healthCheck(): Promise<HealthStatus>
  shutdown(): Promise<void>
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
    actions: Array<'read' | 'write' | 'create' | 'delete' | 'list' | 'execute'>
  }>
  lifecycle?: {
    on_install?: string
    on_uninstall?: string
    on_upgrade?: string
  }
}

export function computeSkillId(manifest: Omit<SkillManifest, 'id'>, sourceFiles: Record<string, string>): string {
  const encoder = new TextEncoder()
  async function sha256(data: string): Promise<string> {
    const hash = await crypto.subtle.digest('SHA-256', encoder.encode(data))
    return Array.from(new Uint8Array(hash))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')
  }

  return sha256(
    JSON.stringify(manifest, Object.keys(manifest).sort()) +
    Object.entries(sourceFiles)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([path, content]) => `${path}\x00${content}\x00`)
      .join('')
  ).then(hash => `skill://sha256/${hash}/${manifest.name}@${manifest.version}`)
}
