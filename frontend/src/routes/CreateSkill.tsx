import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ChevronRight,
  ChevronLeft,
  Package,
  FileKey,
  GitBranch,
  Eye,
  Download,
  Plus,
  Trash2,
  Check,
  Code,
  Rocket,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import Editor from '@monaco-editor/react'
import type { SkillManifest } from '../lib/types'
import { api } from '../lib/api'
import { RequirePermission } from '../components/RequireRole'
import { useAuth } from '../lib/auth'
import MarkdownEditor from '../components/markdown/MarkdownEditor'

const steps = [
  'Basic Info',
  'Capabilities & Permissions',
  'Dependencies & Triggers',
  'Documentation',
  'Review',
]

const defaultBody = (name: string) =>
  `# ${name}\n\nAgent instructions for the **${name}** skill.\n\n## Usage\n\nDescribe how agents interact with this skill.\n\n## Examples\n\nProvide example interactions here.\n`

// Mirrors the backend's strict validators (sdks/python/skill_sdk/validation.py):
// names must be kebab-case starting with a letter, versions must be full SemVer.
const NAME_PATTERN = /^[a-z][a-z0-9-]*$/
const SEMVER_PATTERN = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/

function validateName(name: string): string | null {
  if (!name) return 'Name is required'
  if (!NAME_PATTERN.test(name)) {
    return 'Must be kebab-case (lowercase letters, numbers, hyphens) and start with a letter'
  }
  if (name.length < 2) return 'Name must be at least 2 characters'
  if (name.length > 64) return 'Name must be at most 64 characters'
  return null
}

function validateVersion(version: string): string | null {
  if (!version) return 'Version is required'
  if (!SEMVER_PATTERN.test(version)) {
    return 'Must be a full SemVer version, e.g. 1.0.0 or 1.0.0-rc.1'
  }
  return null
}

const defaultManifest: SkillManifest = {
  name: 'my-skill',
  version: '0.1.0',
  description: '',
  runtime: 'python',
  api_version: 1,
  entry: 'src/main.py',
  capabilities: [],
  permissions: [],
  dependencies: {},
  triggers: {},
  config: { required: [], schema: {} },
  lifecycle: {},
}

export default function CreateSkill() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [manifest, setManifest] = useState<SkillManifest>({ ...defaultManifest, dependencies: {} })
  const [newCapability, setNewCapability] = useState('')
  const [capabilityDuplicate, setCapabilityDuplicate] = useState(false)
  const [permissionActionDuplicate, setPermissionActionDuplicate] = useState(false)
  const [newPermResource, setNewPermResource] = useState('')
  const [newPermAction, setNewPermAction] = useState('')
  const [pipDep, setPipDep] = useState('')
  const [npmDep, setNpmDep] = useState('')
  const [skillDep, setSkillDep] = useState('')
  const [eventTrigger, setEventTrigger] = useState('')
  const [commandTrigger, setCommandTrigger] = useState('')
  const [docBody, setDocBody] = useState('')
  const [docTouched, setDocTouched] = useState(false)

  // Until the author edits the docs, keep them synced to the (changing) skill name.
  const effectiveBody = docTouched ? docBody : defaultBody(manifest.name)

  const queryClient = useQueryClient()
  const { can } = useAuth()

  const update = <K extends keyof SkillManifest>(key: K, value: SkillManifest[K]) =>
    setManifest((m) => ({ ...m, [key]: value }))

  const nameError = validateName(manifest.name)
  const versionError = validateVersion(manifest.version)
  const hasBasicInfoErrors = Boolean(nameError || versionError)

  // Strip empty collections so the scaffolded manifest is clean and minimal.
  const buildManifestPayload = () => {
    const m: Record<string, unknown> = {
      name: manifest.name,
      version: manifest.version,
      runtime: manifest.runtime,
      api_version: manifest.api_version,
      entry: manifest.entry,
    }
    if (manifest.description?.trim()) m.description = manifest.description.trim()
    if (manifest.capabilities?.length) m.capabilities = manifest.capabilities
    if (manifest.permissions?.length) m.permissions = manifest.permissions
    const deps: Record<string, string[]> = {}
    if (manifest.dependencies?.pip?.length) deps.pip = manifest.dependencies.pip
    if (manifest.dependencies?.npm?.length) deps.npm = manifest.dependencies.npm
    if (manifest.dependencies?.skills?.length) deps.skills = manifest.dependencies.skills
    if (Object.keys(deps).length) m.dependencies = deps
    const triggers: Record<string, string[]> = {}
    if (manifest.triggers?.events?.length) triggers.events = manifest.triggers.events
    if (manifest.triggers?.commands?.length) triggers.commands = manifest.triggers.commands
    if (Object.keys(triggers).length) m.triggers = triggers
    if (manifest.config?.required?.length) m.config = { required: manifest.config.required }
    m.body = effectiveBody
    return m as import('../lib/types').ScaffoldRequest['manifest']
  }

  const scaffoldMutation = useMutation({
    mutationFn: (publish: boolean) =>
      api.skills.scaffold({ manifest: buildManifestPayload(), publish }),
    onSuccess: (res) => {
      if (res.success && res.published) {
        queryClient.invalidateQueries({ queryKey: ['skills'] })
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
        queryClient.invalidateQueries({ queryKey: ['audit'] })
      }
    },
  })
  const scaffoldResult = scaffoldMutation.data

  const addCapability = () => {
    const value = newCapability.trim()
    if (!value) return
    if ((manifest.capabilities ?? []).includes(value)) {
      setCapabilityDuplicate(true)
      return
    }
    setCapabilityDuplicate(false)
    update('capabilities', [...(manifest.capabilities ?? []), value])
    setNewCapability('')
  }

  const addPermission = () => {
    const resource = newPermResource.trim()
    const action = newPermAction.trim()
    if (!resource || !action) return
    const existing = manifest.permissions ?? []
    const idx = existing.findIndex((p) => p.resource === resource)
    if (idx >= 0 && existing[idx].actions.includes(action)) {
      setPermissionActionDuplicate(true)
      return
    }
    setPermissionActionDuplicate(false)
    if (idx >= 0) {
      const updated = [...existing]
      updated[idx] = { ...updated[idx], actions: [...new Set([...updated[idx].actions, action])] }
      update('permissions', updated)
    } else {
      update('permissions', [...existing, { resource, actions: [action] }])
    }
    setNewPermAction('')
  }

  const addDependency = (type: 'pip' | 'npm' | 'skills', value: string) => {
    if (!value.trim()) return
    const deps = { ...(manifest.dependencies ?? {}) }
    deps[type] = [...(deps[type] ?? []), value.trim()]
    update('dependencies', deps)
    if (type === 'pip') setPipDep('')
    else if (type === 'npm') setNpmDep('')
    else setSkillDep('')
  }

  const addTrigger = (type: 'events' | 'commands', value: string) => {
    if (!value.trim()) return
    const triggers = { ...(manifest.triggers ?? {}) }
    triggers[type] = [...(triggers[type] ?? []), value.trim()]
    update('triggers', triggers)
    if (type === 'events') setEventTrigger('')
    else setCommandTrigger('')
  }

  const yamlContent = `# ${manifest.name}
name: ${manifest.name}
version: ${manifest.version}
runtime: ${manifest.runtime}
api_version: ${manifest.api_version}
entry: ${manifest.entry}${manifest.description ? `\ndescription: ${manifest.description}` : ''}
${manifest.capabilities && manifest.capabilities.length > 0 ? `\ncapabilities:\n${(manifest.capabilities ?? []).map((c) => `  - ${c}`).join('\n')}` : ''}
${manifest.permissions && manifest.permissions.length > 0 ? `\npermissions:\n${(manifest.permissions ?? []).map((p) => `  - resource: ${p.resource}\n    actions:\n${(p.actions ?? []).map((a) => `      - ${a}`).join('\n')}`).join('\n')}` : ''}
${manifest.dependencies && Object.values(manifest.dependencies).some((v) => v && v.length > 0) ? `\ndependencies:${manifest.dependencies?.pip?.length ? `\n  pip:\n${(manifest.dependencies?.pip ?? []).map((d) => `    - ${d}`).join('\n')}` : ''}${manifest.dependencies?.npm?.length ? `\n  npm:\n${(manifest.dependencies?.npm ?? []).map((d) => `    - ${d}`).join('\n')}` : ''}${manifest.dependencies?.skills?.length ? `\n  skills:\n${(manifest.dependencies?.skills ?? []).map((d) => `    - ${d}`).join('\n')}` : ''}` : ''}
${manifest.triggers?.events?.length || manifest.triggers?.commands?.length ? `\ntriggers:${manifest.triggers?.events?.length ? `\n  events:\n${(manifest.triggers?.events ?? []).map((e) => `    - ${e}`).join('\n')}` : ''}${manifest.triggers?.commands?.length ? `\n  commands:\n${(manifest.triggers?.commands ?? []).map((c) => `    - ${c}`).join('\n')}` : ''}` : ''}
${manifest.config?.required?.length ? `\nconfig:\n  required:\n${(manifest.config?.required ?? []).map((k) => `    - ${k}`).join('\n')}` : ''}
`

  const handleDownload = () => {
    const text = `---\n${yamlContent.trim()}\n---\n\n${effectiveBody.trim()}\n`
    const blob = new Blob([text], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'SKILL.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <RequirePermission
      actions={['skill:create']}
      fallback={
        <div className="card py-16 text-center">
          <Package size={48} className="mx-auto text-ink-3" />
          <p className="mt-4 text-lg font-medium text-ink-2">Permission Denied</p>
          <p className="mt-1 text-sm text-ink-3">You need Developer or Admin role to create skills</p>
          <Link to="/" className="btn-secondary mt-4 inline-flex"><ArrowLeft size={16} /> Back</Link>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate(-1)} className="btn-ghost p-1">
              <ArrowLeft size={20} />
            </button>
            <div>
              <h2 className="text-3xl font-semibold tracking-tightish text-ink">Create Skill</h2>
              <p className="mt-1 text-sm text-ink-2">Define a new skill manifest</p>
            </div>
          </div>
        </div>

        <div className="flex gap-1">
          {steps.map((label, i) => (
            <div key={label} className="flex-1">
              <div className={`h-1 rounded-full transition ${i <= step ? 'bg-accent-500' : 'bg-line'}`} />
              <p className={`mt-2 text-xs font-medium ${i <= step ? 'text-ink' : 'text-ink-3'}`}>
                {label}
              </p>
            </div>
          ))}
        </div>

        {step === 0 && (
          <div className="card space-y-4">
            <h3 className="eyebrow">Basic Information</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink">Name</label>
                <input
                  className="input"
                  placeholder="my-skill"
                  value={manifest.name}
                  onChange={(e) => update('name', e.target.value)}
                  aria-invalid={Boolean(nameError)}
                />
                {nameError && <p className="mt-1 text-xs text-bad">{nameError}</p>}
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink">Version</label>
                <input
                  className="input"
                  placeholder="0.1.0"
                  value={manifest.version}
                  onChange={(e) => update('version', e.target.value)}
                  aria-invalid={Boolean(versionError)}
                />
                {versionError && <p className="mt-1 text-xs text-bad">{versionError}</p>}
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink">Runtime</label>
                <select className="input" value={manifest.runtime} onChange={(e) => update('runtime', e.target.value as 'python' | 'typescript')}>
                  <option value="python">Python</option>
                  <option value="typescript">TypeScript</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink">API Version</label>
                <input type="number" className="input" value={manifest.api_version} onChange={(e) => update('api_version', parseInt(e.target.value) || 1)} />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm font-medium text-ink">Entry Point</label>
                <input className="input font-mono" placeholder="src/main.py" value={manifest.entry} onChange={(e) => update('entry', e.target.value)} />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm font-medium text-ink">Description</label>
                <textarea className="input min-h-[80px] resize-y" placeholder="Optional description" value={manifest.description ?? ''} onChange={(e) => update('description', e.target.value)} />
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div className="card space-y-4">
              <h3 className="eyebrow flex items-center gap-2">
                <FileKey size={14} /> Capabilities
              </h3>
              <div className="flex gap-2">
                <input className="input flex-1" placeholder="Add capability..." value={newCapability} onChange={(e) => { setNewCapability(e.target.value); setCapabilityDuplicate(false) }} onKeyDown={(e) => e.key === 'Enter' && addCapability()} />
                <button onClick={addCapability} className="btn-secondary"><Plus size={16} /> Add</button>
              </div>
              {capabilityDuplicate && <p className="text-xs text-warn">Already added</p>}
              <div className="flex flex-wrap gap-2">
                {(manifest.capabilities ?? []).map((c) => (
                  <span key={c} className="tag flex items-center gap-1">
                    {c}
                    <button onClick={() => update('capabilities', (manifest.capabilities ?? []).filter((x) => x !== c))} className="hover:text-bad">
                      <Trash2 size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="card space-y-4">
              <h3 className="eyebrow flex items-center gap-2">
                <Eye size={14} /> Permissions
              </h3>
              <div className="flex gap-2">
                <input className="input flex-1" placeholder="Resource (e.g. database:orders)" value={newPermResource} onChange={(e) => { setNewPermResource(e.target.value); setPermissionActionDuplicate(false) }} />
                <input className="input w-36" placeholder="Action (e.g. read)" value={newPermAction} onChange={(e) => { setNewPermAction(e.target.value); setPermissionActionDuplicate(false) }} onKeyDown={(e) => e.key === 'Enter' && addPermission()} />
                <button onClick={addPermission} className="btn-secondary"><Plus size={16} /> Add</button>
              </div>
              {permissionActionDuplicate && <p className="text-xs text-warn">Already added</p>}
              <div className="space-y-2">
                {(manifest.permissions ?? []).map((p, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg border border-line p-2">
                    <span className="text-sm text-ink-2">{p.resource}</span>
                    <div className="flex items-center gap-2">
                      {p.actions.map((a) => (
                        <span key={a} className="badge border border-line bg-canvas text-ink-2">{a}</span>
                      ))}
                      <button onClick={() => update('permissions', (manifest.permissions ?? []).filter((_, j) => j !== i))} className="text-ink-3 hover:text-bad">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="card space-y-4">
              <h3 className="eyebrow flex items-center gap-2">
                <GitBranch size={14} /> Dependencies
              </h3>
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-ink-2">Python (pip)</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="requests>=2.0" value={pipDep} onChange={(e) => setPipDep(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDependency('pip', pipDep)} />
                    <button onClick={() => addDependency('pip', pipDep)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.dependencies?.pip ?? []).map((d) => (
                      <span key={d} className="tag flex items-center gap-1">
                        {d}
                        <button onClick={() => update('dependencies', { ...manifest.dependencies, pip: (manifest.dependencies?.pip ?? []).filter((x) => x !== d) })} className="hover:text-bad"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-ink-2">Node.js (npm)</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="lodash" value={npmDep} onChange={(e) => setNpmDep(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDependency('npm', npmDep)} />
                    <button onClick={() => addDependency('npm', npmDep)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.dependencies?.npm ?? []).map((d) => (
                      <span key={d} className="tag flex items-center gap-1">
                        {d}
                        <button onClick={() => update('dependencies', { ...manifest.dependencies, npm: (manifest.dependencies?.npm ?? []).filter((x) => x !== d) })} className="hover:text-bad"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-ink-2">Skills</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="data-quality@1.0" value={skillDep} onChange={(e) => setSkillDep(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDependency('skills', skillDep)} />
                    <button onClick={() => addDependency('skills', skillDep)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.dependencies?.skills ?? []).map((d) => (
                      <span key={d} className="tag flex items-center gap-1">
                        {d}
                        <button onClick={() => update('dependencies', { ...manifest.dependencies, skills: (manifest.dependencies?.skills ?? []).filter((x) => x !== d) })} className="hover:text-bad"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="card space-y-4">
              <h3 className="eyebrow flex items-center gap-2">
                <Code size={14} /> Triggers
              </h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-ink-2">Events</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="schema.updated" value={eventTrigger} onChange={(e) => setEventTrigger(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addTrigger('events', eventTrigger)} />
                    <button onClick={() => addTrigger('events', eventTrigger)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.triggers?.events ?? []).map((e) => (
                      <span key={e} className="tag flex items-center gap-1">
                        {e}
                        <button onClick={() => {
                          const t = { ...manifest.triggers }
                          t.events = (t.events ?? []).filter((x) => x !== e)
                          update('triggers', t)
                        }} className="hover:text-bad"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-ink-2">Commands</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="discover" value={commandTrigger} onChange={(e) => setCommandTrigger(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addTrigger('commands', commandTrigger)} />
                    <button onClick={() => addTrigger('commands', commandTrigger)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.triggers?.commands ?? []).map((c) => (
                      <span key={c} className="tag flex items-center gap-1">
                        {c}
                        <button onClick={() => {
                          const t = { ...manifest.triggers }
                          t.commands = (t.commands ?? []).filter((x) => x !== c)
                          update('triggers', t)
                        }} className="hover:text-bad"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="card space-y-4">
            <div>
              <h3 className="eyebrow">Documentation</h3>
              <p className="mt-1 text-sm text-ink-2">
                Agent-facing instructions (the body of SKILL.md). Markdown and{' '}
                <code className="rounded bg-canvas px-1 py-0.5 text-xs">mermaid</code> diagrams are
                supported — use the Preview tab to check rendering.
              </p>
            </div>
            <MarkdownEditor
              value={effectiveBody}
              onChange={(v) => {
                setDocBody(v)
                setDocTouched(true)
              }}
            />
          </div>
        )}

        {step === 4 && (
          <div className="card space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="eyebrow flex items-center gap-2">
                <FileKey size={14} /> Review Manifest
              </h3>
              <button onClick={handleDownload} className="btn-primary">
                <Download size={16} /> Download SKILL.md
              </button>
            </div>
            <div className="overflow-hidden rounded-lg border border-line">
              <Editor
                height="400px"
                defaultLanguage="yaml"
                value={yamlContent}
                theme="light"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 13,
                  lineNumbers: 'off',
                  folding: false,
                }}
              />
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-line bg-canvas p-3 text-sm text-ink-2">
              <Check size={16} className="text-ok" />
              Manifest is ready. Download it, or scaffold it directly into the server workspace.
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3 border-t border-line pt-4">
              <button
                onClick={() => scaffoldMutation.mutate(false)}
                disabled={scaffoldMutation.isPending || hasBasicInfoErrors}
                className="btn-secondary"
              >
                <Code size={16} /> Scaffold on server
              </button>
              {can('skill:publish') && (
                <button
                  onClick={() => scaffoldMutation.mutate(true)}
                  disabled={scaffoldMutation.isPending || hasBasicInfoErrors}
                  className="btn-primary"
                >
                  <Rocket size={16} /> {scaffoldMutation.isPending ? 'Working...' : 'Scaffold & Publish'}
                </button>
              )}
            </div>

            {scaffoldMutation.isError && (
              <div className="flex items-start gap-2 rounded-lg border border-line bg-canvas p-3 text-sm text-bad">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span className="break-words">
                  {scaffoldMutation.error instanceof Error ? scaffoldMutation.error.message : 'Request failed'}
                </span>
              </div>
            )}

            {scaffoldResult && !scaffoldResult.success && scaffoldResult.errors?.length ? (
              <div className="rounded-lg border border-line bg-canvas p-3 text-sm text-bad">
                <p className="flex items-center gap-2 font-medium"><AlertCircle size={16} /> Validation failed</p>
                <ul className="mt-2 list-disc space-y-1 pl-6 text-xs">
                  {scaffoldResult.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {scaffoldResult?.success && (
              <div className="rounded-lg border border-line bg-canvas p-3 text-sm text-ok">
                <p className="flex items-center gap-2 font-medium">
                  <CheckCircle2 size={16} />
                  {scaffoldResult.published ? 'Scaffolded and published' : 'Scaffolded'}
                </p>
                {scaffoldResult.path && (
                  <p className="mt-1 font-mono text-xs text-ink-3 break-all">{scaffoldResult.path}</p>
                )}
                {scaffoldResult.published && (
                  <button onClick={() => navigate(`/skills/${manifest.name}`)} className="btn-ghost mt-2 text-xs">
                    View in catalog →
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex justify-between">
          <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0} className="btn-ghost">
            <ChevronLeft size={16} /> Back
          </button>
          {step < steps.length - 1 ? (
            <button
              onClick={() => setStep(Math.min(steps.length - 1, step + 1))}
              // Only the basic-info step (0) can have name/version errors, and they're
              // surfaced there. Gating later steps would disable Next with no visible reason.
              disabled={step === 0 && hasBasicInfoErrors}
              className="btn-primary"
            >
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button onClick={() => navigate('/skills')} className="btn-secondary">
              Done
            </button>
          )}
        </div>
      </div>
    </RequirePermission>
  )
}
