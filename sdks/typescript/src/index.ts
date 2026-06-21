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
  description: string
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

/**
 * Deterministic JSON serialization matching Python's
 * `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`:
 * keys are sorted recursively and there is no incidental whitespace. This is the
 * exact byte sequence the Python SDK feeds into the manifest portion of the hash.
 */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value)
  }
  if (Array.isArray(value)) {
    return '[' + value.map(canonicalJson).join(',') + ']'
  }
  const obj = value as Record<string, unknown>
  const keys = Object.keys(obj).sort()
  return (
    '{' +
    keys.map((k) => JSON.stringify(k) + ':' + canonicalJson(obj[k])).join(',') +
    '}'
  )
}

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  // Copy into a freshly-allocated ArrayBuffer: a Uint8Array may be backed by a
  // SharedArrayBuffer, which the WebCrypto BufferSource type rejects.
  const buf = new ArrayBuffer(bytes.byteLength)
  new Uint8Array(buf).set(bytes)
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

/**
 * Compute the content-addressed skill id. Byte-for-byte compatible with the
 * Python `compute_skill_id`:
 *
 *   sha256( canonicalJson(manifest without `id`)
 *           + for each source file (sorted by POSIX path):
 *               relPath + NUL + content + NUL )
 *
 * `sourceFiles` keys MUST be POSIX-relative paths and MUST already exclude the
 * manifest, tests, dotfiles and build dirs (the same set the Python
 * `iter_source_files` yields). Values are UTF-8 text; binary assets are not
 * representable as JS strings and are out of scope for this helper.
 */
export async function computeSkillId(
  manifest: SkillManifest,
  sourceFiles: Record<string, string>,
): Promise<string> {
  const { id: _omit, ...withoutId } = manifest
  const NUL = '\u0000'
  let payload = canonicalJson(withoutId)
  for (const path of Object.keys(sourceFiles).sort()) {
    payload += path + NUL + sourceFiles[path] + NUL
  }
  const bytes = new TextEncoder().encode(payload)
  const hash = await sha256Hex(bytes)
  return `skill://sha256/${hash}/${manifest.name}@${manifest.version}`
}
