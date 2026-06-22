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
    <div className="flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 shadow-soft">
      <div className="flex h-6 w-6 items-center justify-center rounded border border-line bg-canvas text-ink-2">
        <Package size={12} />
      </div>
      <div>
        <p className="text-sm font-semibold text-ink">{data.label}</p>
        <p className="text-[10px] text-ink-3">v{data.latest}</p>
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
  // The host/port we actually connected to, so queries hit the same server.
  const [connectedTo, setConnectedTo] = useState<{ host: string; port: number } | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [capability, setCapability] = useState('')
  const [queryMode, setQueryMode] = useState<'capability' | 'impact' | 'permission'>('capability')
  const [queryResults, setQueryResults] = useState<any[] | null>(null)
  const [querying, setQuerying] = useState(false)
  const [graphError, setGraphError] = useState<string | null>(null)

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
    setGraphError(null)
    const portNum = Number(port)
    if (!Number.isInteger(portNum) || portNum < 1 || portNum > 65535) {
      setGraphError('Port must be a number between 1 and 65535.')
      return
    }
    setConnecting(true)
    try {
      const result = await api.graph.connect(host.trim() || 'localhost', portNum)
      setConnected(result.connected)
      if (result.connected) {
        setConnectedTo({ host: host.trim() || 'localhost', port: portNum })
      } else {
        setGraphError(`Could not connect to FalkorDB at ${host || 'localhost'}:${portNum}.`)
      }
    } catch (e) {
      setConnected(false)
      setGraphError(e instanceof Error ? e.message : 'Connection failed.')
    }
    setConnecting(false)
  }

  const handleDisconnect = () => {
    setConnected(false)
    setConnectedTo(null)
    setQueryResults(null)
    setGraphError(null)
  }

  const handleQuery = async () => {
    if (!capability.trim() || !connectedTo) return
    setGraphError(null)
    setQuerying(true)
    try {
      const result = await api.graph.query(
        queryMode === 'capability'
          ? { capability: capability.trim() }
          : queryMode === 'impact'
            ? { impact_id: capability.trim() }
            : { permission_resource: capability.trim() },
        connectedTo.host,
        connectedTo.port,
      )
      setQueryResults(result.results)
    } catch (e) {
      setQueryResults(null)
      setGraphError(e instanceof Error ? e.message : 'Query failed.')
    }
    setQuerying(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Explore</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Knowledge Graph</h2>
          <p className="mt-2 text-sm text-ink-2">
            Visualize skill relationships and dependencies
          </p>
        </div>
      </div>

      <div className={`card flex items-center gap-4 ${connected ? 'border-ink' : ''}`}>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
          {connected ? <Wifi size={20} /> : <WifiOff size={20} />}
        </div>
        <div className="flex items-center gap-3 flex-1">
          <input
            className="input w-32"
            placeholder="Host"
            aria-label="FalkorDB host"
            value={host}
            disabled={connected}
            onChange={(e) => setHost(e.target.value)}
          />
          <input
            className="input w-24"
            placeholder="Port"
            aria-label="FalkorDB port"
            inputMode="numeric"
            value={port}
            disabled={connected}
            onChange={(e) => setPort(e.target.value)}
          />
          <button
            onClick={connected ? handleDisconnect : handleConnect}
            disabled={connecting}
            className={connected ? 'btn-ghost' : 'btn-secondary'}
          >
            {connecting ? 'Connecting...' : connected ? 'Disconnect' : 'Connect'}
          </button>
        </div>
        {connected && (
          <span className="badge border border-line bg-canvas text-ink-2">
            <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-ok" />
            FalkorDB Connected
          </span>
        )}
        {!connected && (
          <span className="text-xs text-ink-3">
            Showing {entries.length} skill{entries.length !== 1 ? 's' : ''} from registry
          </span>
        )}
      </div>

      {graphError && (
        <div className="flex items-start gap-2 rounded-lg border border-line bg-canvas p-3 text-sm text-ink-2">
          <AlertCircle size={16} className="mt-0.5 shrink-0 text-bad" />
          <span className="break-words">{graphError}</span>
        </div>
      )}

      {connected && (
        <>
          <div className="card flex items-center gap-3">
            <div className="flex gap-1 rounded-lg border border-line bg-canvas p-0.5">
              <button
                onClick={() => setQueryMode('capability')}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  queryMode === 'capability'
                    ? 'bg-surface text-ink shadow-soft'
                    : 'text-ink-2 hover:text-ink'
                }`}
              >
                By Capability
              </button>
              <button
                onClick={() => setQueryMode('impact')}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  queryMode === 'impact'
                    ? 'bg-surface text-ink shadow-soft'
                    : 'text-ink-2 hover:text-ink'
                }`}
              >
                Impact Analysis
              </button>
              <button
                onClick={() => setQueryMode('permission')}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  queryMode === 'permission'
                    ? 'bg-surface text-ink shadow-soft'
                    : 'text-ink-2 hover:text-ink'
                }`}
              >
                By Permission
              </button>
            </div>
            <input
              className="input flex-1"
              placeholder={
                queryMode === 'capability'
                  ? 'Search skills by capability...'
                  : queryMode === 'impact'
                    ? 'Skill ID for impact analysis...'
                    : 'Search skills by permission resource...'
              }
              value={capability}
              aria-label="Graph query input"
              onChange={(e) => setCapability(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            />
            <button onClick={handleQuery} disabled={querying || !capability.trim()} className="btn-primary">
              <Search size={16} /> {querying ? 'Querying...' : 'Query'}
            </button>
          </div>

          {queryResults && (
            <div className="card">
              <h3 className="eyebrow mb-3">
                Query Results ({queryResults.length})
              </h3>
              {queryResults.length === 0 ? (
                <p className="text-sm text-ink-2">No results found</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {queryResults.map((r, i) => (
                    <pre key={i} className="rounded-lg border border-line bg-canvas p-2 text-xs text-ink-2 font-mono overflow-x-auto">
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
          <Network size={48} className="mx-auto text-ink-3" />
          <p className="mt-4 text-lg font-medium text-ink-2">No skills to graph</p>
          <p className="mt-1 text-sm text-ink-3">Publish a skill to see it here</p>
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
              style: { stroke: '#9A9AA0', strokeWidth: 1.5 },
              markerEnd: { type: MarkerType.ArrowClosed, color: '#9A9AA0' },
            }}
          >
            <Controls className="border-line bg-surface text-ink-2" />
            <Background color="#E7E7E3" gap={24} size={1} />
            <MiniMap
              style={{ background: '#F6F6F4', border: '1px solid #E7E7E3' }}
              nodeColor={() => '#E7E7E3'}
              maskColor="rgba(246, 246, 244, 0.8)"
            />
          </ReactFlow>
        </div>
      )}
    </div>
  )
}
