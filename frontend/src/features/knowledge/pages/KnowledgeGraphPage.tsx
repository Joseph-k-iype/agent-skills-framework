import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Empty, Input, Select, Space, Tag, Typography, message } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { GraphExplorer } from "../components/GraphExplorer";
import { useWorkspaceGraph } from "../api/knowledgeApi";
import { useReindexWorkspace } from "@/features/concepts/api/conceptApi";
import { useWorkspaces } from "@/features/workspace/api/workspaceApi";

const TYPE_COLOR: Record<string, string> = {
  skill: "#E82127",
  agent: "#2563EB",
  prompt: "#7C3AED",
  document: "#0F766E",
  workflow: "#B45309",
};

export default function KnowledgeGraphPage() {
  const navigate = useNavigate();
  const workspaces = useWorkspaces();
  const [activeWs, setActiveWs] = useState<string | undefined>();
  const wsId = activeWs ?? workspaces.data?.[0]?.id;

  const graph = useWorkspaceGraph(wsId);
  const reindex = useReindexWorkspace(wsId);

  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());

  const types = useMemo(() => {
    const s = new Set<string>();
    (graph.data?.nodes ?? []).forEach((n) => s.add(n.type?.toLowerCase() || "document"));
    return [...s].sort();
  }, [graph.data]);

  const selectedNode = useMemo(
    () => graph.data?.nodes.find((n) => n.path === selected) ?? null,
    [graph.data, selected],
  );

  const neighbours = useMemo(() => {
    if (!graph.data || !selected) return [] as { path: string; title: string; dir: string }[];
    const titleOf = (p: string) => graph.data!.nodes.find((n) => n.path === p)?.title ?? p;
    const out = graph.data.edges
      .filter((e) => e.source === selected)
      .map((e) => ({ path: e.target, title: titleOf(e.target), dir: "→" }));
    const inc = graph.data.edges
      .filter((e) => e.target === selected)
      .map((e) => ({ path: e.source, title: titleOf(e.source), dir: "←" }));
    return [...out, ...inc];
  }, [graph.data, selected]);

  const toggleType = (t: string) =>
    setHiddenTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });

  const onReindex = () =>
    reindex.mutate(undefined, {
      onSuccess: (r) => {
        message.success(`Reindexed: ${r.documents} doc(s), ${r.embedded} embedded`);
        graph.refetch();
      },
      onError: (e) => message.error((e as Error)?.message ?? "Reindex failed"),
    });

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge"
        title="Knowledge Graph"
        description="Explore every concept in a workspace and how they link together."
        actions={
          <Space>
            <Select
              placeholder="Select workspace"
              style={{ minWidth: 220 }}
              value={wsId}
              onChange={(v) => {
                setActiveWs(v);
                setSelected(null);
                setQuery("");
                setHiddenTypes(new Set());
              }}
              options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
            />
            <Button
              icon={<ReloadOutlined />}
              loading={reindex.isPending}
              disabled={!wsId}
              onClick={onReindex}
              title="Rebuild the graph projection and heal embeddings"
            >
              Reindex
            </Button>
          </Space>
        }
      />

      <Space wrap style={{ marginBottom: 16 }}>
        <Input
          allowClear
          prefix={<SearchOutlined style={{ color: tokens.color.ink3 }} />}
          placeholder="Highlight by name…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: 260 }}
          disabled={!wsId}
        />
        {types.map((t) => {
          const on = !hiddenTypes.has(t);
          return (
            <Tag
              key={t}
              color={on ? TYPE_COLOR[t] ?? "default" : undefined}
              onClick={() => toggleType(t)}
              style={{ cursor: "pointer", opacity: on ? 1 : 0.4, userSelect: "none" }}
            >
              {t}
            </Tag>
          );
        })}
      </Space>

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <GraphExplorer
            data={graph.data}
            selected={selected}
            hiddenTypes={hiddenTypes}
            query={query}
            onSelect={setSelected}
            onOpen={(path) => navigate(`/concepts/${wsId}/${path}`)}
          />
        </div>
        <Card
          title="Details"
          style={{ width: 320, flexShrink: 0 }}
          styles={{ body: { padding: 16 } }}
        >
          {selectedNode ? (
            <Space direction="vertical" size="small" style={{ width: "100%" }}>
              <Typography.Text strong style={{ fontSize: 15 }}>
                {selectedNode.title}
              </Typography.Text>
              <Space size={4} wrap>
                <Tag color={TYPE_COLOR[selectedNode.type?.toLowerCase()] ?? "default"}>
                  {selectedNode.type}
                </Tag>
                {selectedNode.runtime && <Tag bordered={false}>{selectedNode.runtime}</Tag>}
                {selectedNode.versions > 0 && (
                  <Tag bordered={false}>{selectedNode.versions} version(s)</Tag>
                )}
              </Space>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {selectedNode.path}
              </Typography.Text>
              {selectedNode.description && (
                <Typography.Paragraph style={{ marginBottom: 0, fontSize: 13 }}>
                  {selectedNode.description}
                </Typography.Paragraph>
              )}
              <Button
                type="primary"
                size="small"
                onClick={() => navigate(`/concepts/${wsId}/${selectedNode.path}`)}
              >
                Open
              </Button>
              {neighbours.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    Linked concepts
                  </Typography.Text>
                  {neighbours.map((nb, i) => (
                    <div
                      key={`${nb.path}-${i}`}
                      onClick={() => setSelected(nb.path)}
                      style={{ cursor: "pointer", fontSize: 13, padding: "2px 0" }}
                    >
                      <span style={{ color: tokens.color.ink3 }}>{nb.dir}</span> {nb.title}
                    </div>
                  ))}
                </div>
              )}
            </Space>
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Click a node to inspect it"
            />
          )}
        </Card>
      </div>
    </div>
  );
}
