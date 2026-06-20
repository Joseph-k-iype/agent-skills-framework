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

const steps = ['Basic Info', 'Capabilities & Permissions', 'Dependencies & Triggers', 'Review']

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
  const [newPermResource, setNewPermResource] = useState('')
  const [newPermAction, setNewPermAction] = useState('')
  const [pipDep, setPipDep] = useState('')
  const [npmDep, setNpmDep] = useState('')
  const [skillDep, setSkillDep] = useState('')
  const [eventTrigger, setEventTrigger] = useState('')
  const [commandTrigger, setCommandTrigger] = useState('')

  const queryClient = useQueryClient()
  const { can } = useAuth()

  const update = <K extends keyof SkillManifest>(key: K, value: SkillManifest[K]) =>
    setManifest((m) => ({ ...m, [key]: value }))

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
    if (!newCapability.trim()) return
    update('capabilities', [...(manifest.capabilities ?? []), newCapability.trim()])
    setNewCapability('')
  }

  const addPermission = () => {
    if (!newPermResource.trim() || !newPermAction.trim()) return
    const existing = manifest.permissions ?? []
    const idx = existing.findIndex((p) => p.resource === newPermResource.trim())
    if (idx >= 0) {
      const updated = [...existing]
      updated[idx] = { ...updated[idx], actions: [...new Set([...updated[idx].actions, newPermAction.trim()])] }
      update('permissions', updated)
    } else {
      update('permissions', [...existing, { resource: newPermResource.trim(), actions: [newPermAction.trim()] }])
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
    const blob = new Blob([yamlContent], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'skill.yaml'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <RequirePermission
      actions={['skill:create']}
      fallback={
        <div className="card py-16 text-center">
          <Package size={48} className="mx-auto text-gray-700" />
          <p className="mt-4 text-lg font-medium text-gray-400">Permission Denied</p>
          <p className="mt-1 text-sm text-gray-500">You need Developer or Admin role to create skills</p>
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
              <h2 className="text-2xl font-bold text-gray-100">Create Skill</h2>
              <p className="mt-1 text-sm text-gray-400">Define a new skill manifest</p>
            </div>
          </div>
        </div>

        <div className="flex gap-1">
          {steps.map((label, i) => (
            <div key={label} className="flex-1">
              <div className={`h-1 rounded-full transition ${i <= step ? 'bg-brand-600' : 'bg-gray-800'}`} />
              <p className={`mt-2 text-xs font-medium ${i <= step ? 'text-brand-400' : 'text-gray-600'}`}>
                {label}
              </p>
            </div>
          ))}
        </div>

        {step === 0 && (
          <div className="card space-y-4">
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Basic Information</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm text-gray-400">Name</label>
                <input className="input" placeholder="my-skill" value={manifest.name} onChange={(e) => update('name', e.target.value)} />
              </div>
              <div>
                <label className="mb-1.5 block text-sm text-gray-400">Version</label>
                <input className="input" placeholder="0.1.0" value={manifest.version} onChange={(e) => update('version', e.target.value)} />
              </div>
              <div>
                <label className="mb-1.5 block text-sm text-gray-400">Runtime</label>
                <select className="input" value={manifest.runtime} onChange={(e) => update('runtime', e.target.value as 'python' | 'typescript')}>
                  <option value="python">Python</option>
                  <option value="typescript">TypeScript</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm text-gray-400">API Version</label>
                <input type="number" className="input" value={manifest.api_version} onChange={(e) => update('api_version', parseInt(e.target.value) || 1)} />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm text-gray-400">Entry Point</label>
                <input className="input font-mono" placeholder="src/main.py" value={manifest.entry} onChange={(e) => update('entry', e.target.value)} />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm text-gray-400">Description</label>
                <textarea className="input min-h-[80px] resize-y" placeholder="Optional description" value={manifest.description ?? ''} onChange={(e) => update('description', e.target.value)} />
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div className="card space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
                <FileKey size={14} /> Capabilities
              </h3>
              <div className="flex gap-2">
                <input className="input flex-1" placeholder="Add capability..." value={newCapability} onChange={(e) => setNewCapability(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addCapability()} />
                <button onClick={addCapability} className="btn-secondary"><Plus size={16} /> Add</button>
              </div>
              <div className="flex flex-wrap gap-2">
                {(manifest.capabilities ?? []).map((c) => (
                  <span key={c} className="tag bg-brand-600/10 text-brand-400 flex items-center gap-1">
                    {c}
                    <button onClick={() => update('capabilities', (manifest.capabilities ?? []).filter((x) => x !== c))} className="hover:text-red-400">
                      <Trash2 size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="card space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
                <Eye size={14} /> Permissions
              </h3>
              <div className="flex gap-2">
                <input className="input flex-1" placeholder="Resource (e.g. database:orders)" value={newPermResource} onChange={(e) => setNewPermResource(e.target.value)} />
                <input className="input w-36" placeholder="Action (e.g. read)" value={newPermAction} onChange={(e) => setNewPermAction(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addPermission()} />
                <button onClick={addPermission} className="btn-secondary"><Plus size={16} /> Add</button>
              </div>
              <div className="space-y-2">
                {(manifest.permissions ?? []).map((p, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg border border-gray-800 p-2">
                    <span className="text-sm text-gray-300">{p.resource}</span>
                    <div className="flex items-center gap-2">
                      {p.actions.map((a) => (
                        <span key={a} className="badge bg-gray-800 text-gray-400">{a}</span>
                      ))}
                      <button onClick={() => update('permissions', (manifest.permissions ?? []).filter((_, j) => j !== i))} className="text-gray-600 hover:text-red-400">
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
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
                <GitBranch size={14} /> Dependencies
              </h3>
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1.5 block text-xs text-gray-500">Python (pip)</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="requests>=2.0" value={pipDep} onChange={(e) => setPipDep(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDependency('pip', pipDep)} />
                    <button onClick={() => addDependency('pip', pipDep)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.dependencies?.pip ?? []).map((d) => (
                      <span key={d} className="tag bg-gray-800 text-gray-300 flex items-center gap-1">
                        {d}
                        <button onClick={() => update('dependencies', { ...manifest.dependencies, pip: (manifest.dependencies?.pip ?? []).filter((x) => x !== d) })} className="hover:text-red-400"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-gray-500">Node.js (npm)</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="lodash" value={npmDep} onChange={(e) => setNpmDep(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDependency('npm', npmDep)} />
                    <button onClick={() => addDependency('npm', npmDep)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.dependencies?.npm ?? []).map((d) => (
                      <span key={d} className="tag bg-gray-800 text-gray-300 flex items-center gap-1">
                        {d}
                        <button onClick={() => update('dependencies', { ...manifest.dependencies, npm: (manifest.dependencies?.npm ?? []).filter((x) => x !== d) })} className="hover:text-red-400"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-gray-500">Skills</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="data-quality@1.0" value={skillDep} onChange={(e) => setSkillDep(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDependency('skills', skillDep)} />
                    <button onClick={() => addDependency('skills', skillDep)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.dependencies?.skills ?? []).map((d) => (
                      <span key={d} className="tag bg-brand-600/10 text-brand-400 flex items-center gap-1">
                        {d}
                        <button onClick={() => update('dependencies', { ...manifest.dependencies, skills: (manifest.dependencies?.skills ?? []).filter((x) => x !== d) })} className="hover:text-red-400"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="card space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
                <Code size={14} /> Triggers
              </h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs text-gray-500">Events</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="schema.updated" value={eventTrigger} onChange={(e) => setEventTrigger(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addTrigger('events', eventTrigger)} />
                    <button onClick={() => addTrigger('events', eventTrigger)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.triggers?.events ?? []).map((e) => (
                      <span key={e} className="tag bg-gray-800 text-gray-300 flex items-center gap-1">
                        {e}
                        <button onClick={() => {
                          const t = { ...manifest.triggers }
                          t.events = (t.events ?? []).filter((x) => x !== e)
                          update('triggers', t)
                        }} className="hover:text-red-400"><Trash2 size={10} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-gray-500">Commands</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="discover" value={commandTrigger} onChange={(e) => setCommandTrigger(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addTrigger('commands', commandTrigger)} />
                    <button onClick={() => addTrigger('commands', commandTrigger)} className="btn-ghost p-2"><Plus size={14} /></button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(manifest.triggers?.commands ?? []).map((c) => (
                      <span key={c} className="tag bg-gray-800 text-gray-300 flex items-center gap-1">
                        {c}
                        <button onClick={() => {
                          const t = { ...manifest.triggers }
                          t.commands = (t.commands ?? []).filter((x) => x !== c)
                          update('triggers', t)
                        }} className="hover:text-red-400"><Trash2 size={10} /></button>
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
            <div className="flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
                <FileKey size={14} /> Review Manifest
              </h3>
              <button onClick={handleDownload} className="btn-primary">
                <Download size={16} /> Download skill.yaml
              </button>
            </div>
            <div className="overflow-hidden rounded-lg border border-gray-800">
              <Editor
                height="400px"
                defaultLanguage="yaml"
                value={yamlContent}
                theme="vs-dark"
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
            <div className="flex items-center gap-2 rounded-lg bg-gray-800/60 p-3 text-sm text-gray-400">
              <Check size={16} className="text-emerald-400" />
              Manifest is ready. Download it, or scaffold it directly into the server workspace.
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-800 pt-4">
              <button
                onClick={() => scaffoldMutation.mutate(false)}
                disabled={scaffoldMutation.isPending}
                className="btn-secondary"
              >
                <Code size={16} /> Scaffold on server
              </button>
              {can('skill:publish') && (
                <button
                  onClick={() => scaffoldMutation.mutate(true)}
                  disabled={scaffoldMutation.isPending}
                  className="btn-primary"
                >
                  <Rocket size={16} /> {scaffoldMutation.isPending ? 'Working...' : 'Scaffold & Publish'}
                </button>
              )}
            </div>

            {scaffoldMutation.isError && (
              <div className="flex items-start gap-2 rounded-lg bg-red-600/10 p-3 text-sm text-red-400">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span className="break-words">
                  {scaffoldMutation.error instanceof Error ? scaffoldMutation.error.message : 'Request failed'}
                </span>
              </div>
            )}

            {scaffoldResult && !scaffoldResult.success && scaffoldResult.errors?.length ? (
              <div className="rounded-lg bg-red-600/10 p-3 text-sm text-red-400">
                <p className="flex items-center gap-2 font-medium"><AlertCircle size={16} /> Validation failed</p>
                <ul className="mt-2 list-disc space-y-1 pl-6 text-xs">
                  {scaffoldResult.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {scaffoldResult?.success && (
              <div className="rounded-lg bg-emerald-600/10 p-3 text-sm text-emerald-400">
                <p className="flex items-center gap-2 font-medium">
                  <CheckCircle2 size={16} />
                  {scaffoldResult.published ? 'Scaffolded and published' : 'Scaffolded'}
                </p>
                {scaffoldResult.path && (
                  <p className="mt-1 font-mono text-xs text-emerald-500/80 break-all">{scaffoldResult.path}</p>
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
            <button onClick={() => setStep(Math.min(steps.length - 1, step + 1))} className="btn-primary">
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
