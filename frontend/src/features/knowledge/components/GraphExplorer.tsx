import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useMemo } from "react";
import { Empty } from "antd";
import type { GraphNode, WorkspaceGraph } from "../api/knowledgeApi";
import { tokens } from "@/app/theme/tokens";

const TYPE_COLOR: Record<string, string> = {
  skill: "#E82127",
  agent: "#2563EB",
  prompt: "#7C3AED",
  document: "#0F766E",
  workflow: "#B45309",
};
const typeColor = (t: string) => TYPE_COLOR[t?.toLowerCase()] ?? tokens.color.ink2;

export interface GraphExplorerProps {
  data: WorkspaceGraph | undefined;
  selected: string | null;
  hiddenTypes: Set<string>;
  query: string;
  onSelect: (path: string) => void;
  onOpen: (path: string) => void;
}

/** Auto-laid-out workspace graph: hubs are larger, nodes colored by type. */
export function GraphExplorer({
  data,
  selected,
  hiddenTypes,
  query,
  onSelect,
  onOpen,
}: GraphExplorerProps) {
  const { nodes, edges, count } = useMemo(() => {
    if (!data || data.nodes.length === 0) {
      return { nodes: [] as Node[], edges: [] as Edge[], count: 0 };
    }

    const visible = data.nodes.filter((n) => !hiddenTypes.has(n.type?.toLowerCase()));
    const visiblePaths = new Set(visible.map((n) => n.path));
    const links = data.edges.filter(
      (e) => visiblePaths.has(e.source) && visiblePaths.has(e.target),
    );

    // Degree drives hub sizing; neighbours drive selection highlight.
    const degree = new Map<string, number>();
    const neighbours = new Map<string, Set<string>>();
    visible.forEach((n) => neighbours.set(n.path, new Set()));
    links.forEach((e) => {
      degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
      degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
      neighbours.get(e.source)?.add(e.target);
      neighbours.get(e.target)?.add(e.source);
    });

    const q = query.trim().toLowerCase();
    const isMatch = (n: GraphNode) =>
      q.length > 0 && (n.title.toLowerCase().includes(q) || n.path.toLowerCase().includes(q));
    const inFocus = (path: string) => {
      if (selected) return path === selected || (neighbours.get(selected)?.has(path) ?? false);
      return true;
    };

    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: "LR", nodesep: 36, ranksep: 90, marginx: 20, marginy: 20 });

    const sizeOf = (path: string) => {
      const d = degree.get(path) ?? 0;
      const w = Math.min(220, 130 + d * 14);
      return { w, h: 46 };
    };
    visible.forEach((n) => {
      const { w, h } = sizeOf(n.path);
      g.setNode(n.path, { width: w, height: h });
    });
    links.forEach((e) => g.setEdge(e.source, e.target));
    dagre.layout(g);

    const rfNodes: Node[] = visible.map((n) => {
      const pos = g.node(n.path);
      const { w, h } = sizeOf(n.path);
      const focused = inFocus(n.path);
      const matched = isMatch(n);
      const color = typeColor(n.type);
      const isSel = n.path === selected;
      return {
        id: n.path,
        position: { x: pos.x - w / 2, y: pos.y - h / 2 },
        data: { label: n.versions > 0 ? `${n.title}  ·v${n.versions}` : n.title },
        style: {
          width: w,
          minHeight: h,
          background: isSel ? color : tokens.color.surface,
          color: isSel ? "#fff" : tokens.color.ink,
          border: `${matched ? 2 : 1}px solid ${matched ? tokens.color.warn : color}`,
          borderRadius: 10,
          padding: "8px 12px",
          fontSize: 12,
          fontWeight: isSel ? 700 : 500,
          opacity: focused ? 1 : 0.22,
          textAlign: "center",
        },
      };
    });

    const rfEdges: Edge[] = links.map((e, i) => {
      const focused = !selected || e.source === selected || e.target === selected;
      return {
        id: `${e.source}->${e.target}-${i}`,
        source: e.source,
        target: e.target,
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        style: { stroke: tokens.color.line, opacity: focused ? 1 : 0.12 },
      };
    });

    return { nodes: rfNodes, edges: rfEdges, count: visible.length };
  }, [data, hiddenTypes, query, selected]);

  if (!data || data.nodes.length === 0) {
    return (
      <div style={{ height: 560, display: "grid", placeItems: "center" }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No concepts yet — create some, then Reindex"
        />
      </div>
    );
  }

  return (
    <div
      style={{
        height: 560,
        border: `1px solid ${tokens.color.line}`,
        borderRadius: tokens.radius,
        position: "relative",
      }}
    >
      <ReactFlow
        key={count}
        nodes={nodes}
        edges={edges}
        fitView
        minZoom={0.2}
        nodesDraggable={false}
        onNodeClick={(_, n) => onSelect(n.id)}
        onNodeDoubleClick={(_, n) => onOpen(n.id)}
        proOptions={{ hideAttribution: true }}
      >
        <Background color={tokens.color.line} gap={22} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default GraphExplorer;
