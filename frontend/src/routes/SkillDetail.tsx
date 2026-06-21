import { useState, useMemo, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Package,
  ArrowLeft,
  XCircle,
  FileText,
  Layers,
  GitBranch,
  Hash,
  Terminal,
  Download,
  ClipboardCheck,
  Pencil,
  Save,
  X,
} from 'lucide-react'
import MarkdownPreview from '../components/markdown/MarkdownPreview'
import MarkdownEditor from '../components/markdown/MarkdownEditor'
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MarkerType,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { api } from '../lib/api'
import { shortHash } from '../lib/utils'
import InstallModal from '../components/InstallModal'
import EvaluationPanel from '../components/EvaluationPanel'
import { RequirePermission } from '../components/RequireRole'

type Tab = 'manifest' | 'docs' | 'versions' | 'dependencies' | 'evaluation'

function DepNode({ data }: { data: { label: string; type: string } }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs font-medium text-ink shadow-sm">
      {data.label}
    </div>
  )
}

const depNodeTypes: NodeTypes = { depNode: DepNode }

export default function SkillDetail() {
  const { name } = useParams<{ name: string }>()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('manifest')
  const [installOpen, setInstallOpen] = useState(false)
  const [editingDocs, setEditingDocs] = useState(false)
  const [draftBody, setDraftBody] = useState('')

  const saveDocs = useMutation({
    mutationFn: (body: string) => api.skills.updateDoc(name!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-manifest', name] })
      queryClient.invalidateQueries({ queryKey: ['skill-doc', name] })
      setEditingDocs(false)
    },
  })

  const { data: detail, isLoading: detailLoading, error: detailError } = useQuery({
    queryKey: ['skill', name],
    queryFn: () => api.skills.detail(name!),
    enabled: !!name,
  })

  const { data: manifestRes } = useQuery({
    queryKey: ['skill-manifest', name],
    queryFn: () => api.skills.manifest(name!),
    enabled: !!name && (activeTab === 'manifest' || activeTab === 'docs'),
  })

  const { data: docRes } = useQuery({
    queryKey: ['skill-doc', name],
    queryFn: () => api.skills.doc(name!),
    enabled: !!name && activeTab === 'docs',
  })

  const { data: versions } = useQuery({
    queryKey: ['skill-versions', name],
    queryFn: () => api.skills.versions(name!),
    // Fetched eagerly (not just on the Versions tab) so the Install modal has
    // the full, SemVer-ordered version list available immediately.
    enabled: !!name,
  })

  const { data: validateRes } = useQuery({
    queryKey: ['skill-validate', name],
    queryFn: () => api.skills.validate(name!),
    enabled: !!name,
  })

  const manifest = manifestRes?.manifest
  const manifestBody = manifestRes?.body
  const manifestRaw = manifestRes?.raw
  const deps = manifest?.dependencies

  const { nodes: depNodes, edges: depEdges } = useMemo(() => {
    const n: any[] = []
    const e: any[] = []
    if (!deps) return { nodes: n, edges: e }

    const centerX = 250
    const centerY = 150

    n.push({
      id: 'skill',
      type: 'depNode',
      position: { x: centerX, y: centerY },
      data: { label: name ?? 'skill', type: 'skill' },
      style: { fontSize: 14, fontWeight: 600 },
    })

    let idx = 0
    const addNodes = (items: string[] | undefined, type: string, color: string) => {
      if (!items) return
      items.forEach((item) => {
        const id = `${type}-${idx}`
        const angle = (2 * Math.PI * idx) / 8 - Math.PI / 2
        const radius = 120
        n.push({
          id,
          type: 'depNode',
          position: { x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) },
          data: { label: item, type },
        })
        e.push({
          id: `skill->${id}`,
          source: 'skill',
          target: id,
          style: { stroke: '#C9C9C4', strokeWidth: 1 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#C9C9C4' },
        })
        idx++
      })
    }

    addNodes(deps.pip, 'pip', 'amber')
    addNodes(deps.npm, 'npm', 'emerald')
    addNodes(deps.skills, 'skill', 'brand')

    return { nodes: n, edges: e }
  }, [deps, name])

  const [nodes, setNodes, onNodesChange] = useNodesState(depNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(depEdges)

  // Sync derived graph into React Flow state when dependencies change. This is a
  // side effect, so it must be useEffect — doing it in useMemo updates state
  // during render and triggers React's "cannot update while rendering" warning.
  useEffect(() => {
    setNodes(depNodes)
    setEdges(depEdges)
  }, [depNodes, depEdges, setNodes, setEdges])

  if (detailLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-canvas" />
        <div className="h-64 animate-pulse rounded-lg bg-canvas" />
      </div>
    )
  }

  if (detailError || !detail) {
    return (
      <div className="card py-16 text-center">
        <XCircle size={48} className="mx-auto text-ink-3" />
        <p className="mt-4 text-lg font-medium text-ink-2">Skill not found</p>
        <Link to="/skills" className="btn-secondary mt-4 inline-flex">
          <ArrowLeft size={16} /> Back to Catalog
        </Link>
      </div>
    )
  }

  const skillId = detail.ids?.[detail.latest]
  const doc = docRes?.doc
  const valid = validateRes?.valid

  const tabs: { key: Tab; label: string; icon: typeof FileText }[] = [
    { key: 'manifest', label: 'Manifest', icon: FileText },
    { key: 'docs', label: 'Documentation', icon: Terminal },
    { key: 'versions', label: 'Versions', icon: Layers },
    { key: 'dependencies', label: 'Dependencies', icon: GitBranch },
    { key: 'evaluation', label: 'Evaluation', icon: ClipboardCheck },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/skills" className="btn-ghost p-1">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-line bg-canvas text-ink-2">
          <Package size={24} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tightish text-ink">{name}</h2>
            <span className="badge bg-canvas border border-line font-mono text-ink-2">{detail.latest}</span>
            {valid === true && (
              <span className="badge bg-canvas border border-line text-ink-2">
                <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                Valid
              </span>
            )}
            {valid === false && (
              <span className="badge bg-canvas border border-line text-ink-2">
                <span className="h-1.5 w-1.5 rounded-full bg-bad" />
                Invalid
              </span>
            )}
          </div>
          <p className="text-sm text-ink-2">
            {detail.versions?.length ?? 0} versions published
          </p>
        </div>
        <RequirePermission actions={['skill:install']}>
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => setInstallOpen(true)}>
              <Download size={16} />
              Install
            </button>
          </div>
        </RequirePermission>
      </div>

      {manifest && (
        <div className="card flex flex-wrap items-center gap-4">
          {manifest.runtime && (
            <div className="flex items-center gap-2 text-sm text-ink-2">
              <Terminal size={14} className="text-ink-3" />
              <span className="tag">{manifest.runtime}</span>
            </div>
          )}
          {skillId && (
            <div className="flex items-center gap-2 text-sm text-ink-2">
              <Hash size={14} className="text-ink-3" />
              <span className="font-mono text-xs text-ink-3">{skillId}</span>
            </div>
          )}
          {manifest.description && (
            <p className="w-full text-sm text-ink-2">{manifest.description}</p>
          )}
        </div>
      )}

      <div className="border-b border-line">
        <div className="flex gap-0 -mb-px">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={activeTab === key ? 'tab-active flex items-center gap-2' : 'tab flex items-center gap-2'}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div>
        {activeTab === 'manifest' && (
          <div className="card">
            {manifestRaw ? (
              <pre className="overflow-x-auto rounded-lg border border-line bg-canvas p-4 text-sm text-ink font-mono leading-relaxed">
                {manifestRaw}
              </pre>
            ) : manifest ? (
              <pre className="overflow-x-auto rounded-lg border border-line bg-canvas p-4 text-sm text-ink font-mono leading-relaxed">
                {JSON.stringify(manifest, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-ink-3">Loading manifest...</p>
            )}
          </div>
        )}

        {activeTab === 'docs' && (
          <div className="space-y-3">
            {editingDocs ? (
              <>
                <MarkdownEditor value={draftBody} onChange={setDraftBody} />
                {saveDocs.isError && (
                  <p className="text-sm text-bad">
                    {saveDocs.error instanceof Error ? saveDocs.error.message : 'Save failed'}
                  </p>
                )}
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => setEditingDocs(false)}
                    className="btn-secondary"
                    disabled={saveDocs.isPending}
                  >
                    <X size={16} /> Cancel
                  </button>
                  <button
                    onClick={() => saveDocs.mutate(draftBody)}
                    className="btn-primary"
                    disabled={saveDocs.isPending}
                  >
                    <Save size={16} /> {saveDocs.isPending ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <RequirePermission actions={['skill:create']}>
                  <div className="flex justify-end">
                    <button
                      onClick={() => {
                        setDraftBody(manifestBody ?? '')
                        setEditingDocs(true)
                      }}
                      className="btn-secondary"
                    >
                      <Pencil size={16} /> Edit
                    </button>
                  </div>
                </RequirePermission>
                <div className="card">
                  {manifestBody !== undefined ? (
                    <MarkdownPreview content={manifestBody || doc || ''} />
                  ) : doc ? (
                    <MarkdownPreview content={doc} />
                  ) : (
                    <p className="text-sm text-ink-3">Loading documentation...</p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'versions' && (
          <div className="space-y-2">
            {versions?.versions?.length ? (
              [...versions.versions].reverse().map((ver) => {
                const vid = versions.ids?.[ver]
                return (
                  <div key={ver} className="card flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
                        <Layers size={14} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-ink">
                          v{ver}
                          {ver === versions.latest && (
                            <span className="ml-2 badge bg-canvas border border-line text-ink-2 text-[10px]">Latest</span>
                          )}
                        </p>
                        {vid && <p className="text-xs text-ink-3 font-mono">{shortHash(vid)}</p>}
                      </div>
                    </div>
                    {vid && <span className="text-xs text-ink-3 font-mono hidden sm:block">{vid}</span>}
                  </div>
                )
              })
            ) : (
              <p className="text-sm text-ink-3">No version history yet</p>
            )}
          </div>
        )}

        {activeTab === 'dependencies' && (
          <div className="space-y-4">
            <div className="card">
              {manifest?.dependencies ? (
                <div className="space-y-4">
                  {deps?.pip && deps.pip.length > 0 && (
                    <div>
                      <h4 className="eyebrow mb-2">Python (pip)</h4>
                      <div className="flex flex-wrap gap-2">
                        {deps.pip.map((dep) => (
                          <span key={dep} className="tag">{dep}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {deps?.npm && deps.npm.length > 0 && (
                    <div>
                      <h4 className="eyebrow mb-2">Node.js (npm)</h4>
                      <div className="flex flex-wrap gap-2">
                        {deps.npm.map((dep) => (
                          <span key={dep} className="tag">{dep}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {deps?.skills && deps.skills.length > 0 && (
                    <div>
                      <h4 className="eyebrow mb-2">Skills</h4>
                      {deps.skills.map((dep) => {
                        const depName = dep.split('@')[0]
                        return (
                          <Link
                            key={dep}
                            to={`/skills/${depName}`}
                            className="tag text-ink-2 hover:text-ink hover:border-accent-200 inline-flex mr-2 mb-2"
                          >
                            {dep}
                          </Link>
                        )
                      })}
                    </div>
                  )}
                  {!deps?.pip?.length && !deps?.npm?.length && !deps?.skills?.length && (
                    <p className="text-sm text-ink-3">No dependencies declared</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-ink-3">Loading dependencies...</p>
              )}
            </div>

            {deps && (deps.pip?.length || deps.npm?.length || deps.skills?.length) && (
              <div className="card overflow-hidden" style={{ height: 350 }}>
                <h4 className="eyebrow mb-3">Dependency Graph</h4>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  nodeTypes={depNodeTypes}
                  fitView
                  minZoom={0.3}
                  maxZoom={2}
                  proOptions={{ hideAttribution: true }}
                >
                  <Controls className="bg-surface border-line text-ink-2" />
                  <Background color="#E7E7E3" gap={20} size={1} />
                </ReactFlow>
              </div>
            )}
          </div>
        )}

        {activeTab === 'evaluation' && (
          <EvaluationPanel skillName={name!} version={detail.latest} />
        )}
      </div>

      <InstallModal
        open={installOpen}
        onClose={() => setInstallOpen(false)}
        skillName={name ?? ''}
        versions={versions?.versions ?? [detail.latest]}
        latest={detail.latest}
      />
    </div>
  )
}
