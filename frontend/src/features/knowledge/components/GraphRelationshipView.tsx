import { Background, Controls, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useMemo } from "react";
import { Empty } from "antd";
import { tokens } from "@/app/theme/tokens";
import type { Neighborhood } from "../api/knowledgeApi";

/** Renders a node and its immediate relationships in a radial layout. */
export function GraphRelationshipView({ data }: { data: Neighborhood | undefined }) {
  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const center: Node = {
      id: data.node.id,
      position: { x: 0, y: 0 },
      data: { label: data.node.title ?? data.node.name ?? data.node.id },
      style: {
        background: tokens.color.ink,
        color: "#fff",
        border: "none",
        borderRadius: 10,
        padding: "8px 14px",
        fontWeight: 600,
      },
    };
    const n = data.edges.length;
    const radius = Math.min(260, 120 + n * 18);
    const nodes: Node[] = [center];
    const edges: Edge[] = [];
    data.edges.forEach((e, i) => {
      const angle = (2 * Math.PI * i) / Math.max(n, 1);
      nodes.push({
        id: e.id,
        position: { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius },
        data: { label: e.label },
        style: {
          background: tokens.color.surface,
          border: `1px solid ${tokens.color.lineStrong}`,
          borderRadius: 10,
          padding: "6px 12px",
        },
      });
      edges.push({
        id: `${e.dir}-${e.id}-${i}`,
        source: e.dir === "out" ? data.node.id : e.id,
        target: e.dir === "out" ? e.id : data.node.id,
        label: e.rel,
        animated: e.dir === "out",
        style: { stroke: tokens.color.line },
        labelStyle: { fontSize: 10, fill: tokens.color.ink3 },
      });
    });
    return { nodes, edges };
  }, [data]);

  if (!data) {
    return (
      <div style={{ height: 460, display: "grid", placeItems: "center" }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Select a result to explore its relationships" />
      </div>
    );
  }

  return (
    <div style={{ height: 460, border: `1px solid ${tokens.color.line}`, borderRadius: tokens.radius }}>
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Background color={tokens.color.line} gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
