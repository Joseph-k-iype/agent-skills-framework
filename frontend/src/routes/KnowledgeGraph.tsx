import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  MarkerType,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Network, Wifi, WifiOff, Search, AlertCircle, Package } from 'lucide-react'
import { api } from '../lib/api'
import type { SkillEntry } from '../lib/types'

function SkillNode({ data }: { data: { label: string; hash?: string; latest: string } }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 shadow-lg">
      <div className="flex h-6 w-6 items-center justify-center rounded bg-brand-600/20 text-brand-400">
        <Package size={12} />
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-200">{data.label}</p>
        <p className="text-[10px] text-gray-500">v{data.latest}</p>
      </div>
    </div>
  )
}

const nodeTypes: NodeTypes = {
  skillNode: SkillNode,
}

function buildGraphLayout(entries: [string, SkillEntry][]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []
  const count = entries.length
  if (count === 0) return { nodes, edges }

  const centerX = 400
  const centerY = 300
  const radius = Math.min(centerX, centerY) - 60

  entries.forEach(([name, info], i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2
    nodes.push({
      id: name,
      type: 'skillNode',
      position: {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      },
      data: { label: name, latest: info.latest, hash: info.ids?.[info.latest] },
    })
  })

  return { nodes, edges }
}

export default function KnowledgeGraph() {
  const [host, setHost] = useState('localhost')
  const [port, setPort] = useState('6379')
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [capability, setCapability] = useState('')
  const [queryMode, setQueryMode] = useState<'capability' | 'impact'>('capability')
  const [queryResults, setQueryResults] = useState<any[] | null>(null)

  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: api.skills.list,
  })

  const entries = useMemo(
    () => Object.entries(skills ?? {}),
    [skills]
  )

  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(
    () => buildGraphLayout(entries),
    [entries]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutEdges)

  // Side effect → useEffect (not useMemo, which would setState during render).
  useEffect(() => {
    setNodes(layoutNodes)
    setEdges(layoutEdges)
  }, [layoutNodes, layoutEdges, setNodes, setEdges])

  const handleConnect = async () => {
    setConnecting(true)
    try {
      const result = await api.graph.connect(host, parseInt(port))
      setConnected(result.connected)
    } catch {
      setConnected(false)
    }
    setConnecting(false)
  }

  const handleQuery = async () => {
    if (!capability.trim()) return
    try {
      const result = await api.graph.query(
        queryMode === 'capability'
          ? { capability: capability.trim() }
          : { impact_id: capability.trim() }
      )
      setQueryResults(result.results)
    } catch {
      setQueryResults([])
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Knowledge Graph</h2>
          <p className="mt-1 text-sm text-gray-400">
            Visualize skill relationships and dependencies
          </p>
        </div>
      </div>

      <div className={`card flex items-center gap-4 ${connected ? 'border-emerald-600/30' : ''}`}>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
          connected ? 'bg-emerald-600/10 text-emerald-400' : 'bg-gray-800 text-gray-500'
        }`}>
          {connected ? <Wifi size={20} /> : <WifiOff size={20} />}
        </div>
        <div className="flex items-center gap-3 flex-1">
          <input
            className="input w-32"
            placeholder="Host"
            value={host}
            onChange={(e) => setHost(e.target.value)}
          />
          <input
            className="input w-24"
            placeholder="Port"
            value={port}
            onChange={(e) => setPort(e.target.value)}
          />
          <button
            onClick={connected ? () => setConnected(false) : handleConnect}
            disabled={connecting}
            className={connected ? 'btn-ghost' : 'btn-secondary'}
          >
            {connecting ? 'Connecting...' : connected ? 'Disconnect' : 'Connect'}
          </button>
        </div>
        {connected && (
          <span className="badge bg-emerald-600/10 text-emerald-400">FalkorDB Connected</span>
        )}
        {!connected && (
          <span className="text-xs text-gray-500">
            Showing {entries.length} skill{entries.length !== 1 ? 's' : ''} from registry
          </span>
        )}
      </div>

      {connected && (
        <>
          <div className="card flex items-center gap-3">
            <div className="flex gap-1 rounded-lg bg-gray-800 p-0.5">
              <button
                onClick={() => setQueryMode('capability')}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  queryMode === 'capability'
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                By Capability
              </button>
              <button
                onClick={() => setQueryMode('impact')}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  queryMode === 'impact'
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Impact Analysis
              </button>
            </div>
            <input
              className="input flex-1"
              placeholder={
                queryMode === 'capability'
                  ? 'Search skills by capability...'
                  : 'Skill ID for impact analysis...'
              }
              value={capability}
              onChange={(e) => setCapability(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            />
            <button onClick={handleQuery} className="btn-primary">
              <Search size={16} /> Query
            </button>
          </div>

          {queryResults && (
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Query Results ({queryResults.length})
              </h3>
              {queryResults.length === 0 ? (
                <p className="text-sm text-gray-500">No results found</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {queryResults.map((r, i) => (
                    <pre key={i} className="rounded bg-gray-800 p-2 text-xs text-gray-300 font-mono overflow-x-auto">
                      {JSON.stringify(r, null, 2)}
                    </pre>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {entries.length === 0 ? (
        <div className="card py-16 text-center">
          <Network size={48} className="mx-auto text-gray-700" />
          <p className="mt-4 text-lg font-medium text-gray-400">No skills to graph</p>
          <p className="mt-1 text-sm text-gray-500">Publish a skill to see it here</p>
        </div>
      ) : (
        <div className="card overflow-hidden" style={{ height: 520 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.3}
            maxZoom={2}
            defaultEdgeOptions={{
              style: { stroke: '#334155', strokeWidth: 1.5 },
              markerEnd: { type: MarkerType.ArrowClosed, color: '#334155' },
            }}
          >
            <Controls className="bg-gray-900 border-gray-800 text-gray-400" />
            <Background color="#1e293b" gap={24} size={1} />
            <MiniMap
              style={{ background: '#0f172a', border: '1px solid #1e293b' }}
              nodeColor={() => '#1e293b'}
              maskColor="rgba(15, 23, 42, 0.8)"
            />
          </ReactFlow>
        </div>
      )}
    </div>
  )
}
