import { Card, Col, Empty, Row, Select, Statistic, Table, Tag } from "antd";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { useAnalyticsOverview } from "../api/analyticsApi";
import { useWorkspaces } from "@/features/workspace/api/workspaceApi";

const TYPE_COLOR: Record<string, string> = {
  skill: "#E82127",
  agent: "#2563EB",
  prompt: "#7C3AED",
  document: "#0F766E",
  workflow: "#B45309",
};
const KIND_LABEL: Record<string, string> = {
  fast: "Fast (rules)",
  deep: "Deep (effectiveness)",
  grade: "Grade (pass-rate)",
};

export default function InsightsPage() {
  const workspaces = useWorkspaces();
  const [activeWs, setActiveWs] = useState<string | undefined>();
  const wsId = activeWs ?? workspaces.data?.[0]?.id;
  const overview = useAnalyticsOverview(wsId);
  const d = overview.data;

  const typeData = (d?.graph?.types ?? []).map((t) => ({ name: t.type || "—", value: t.count }));
  const kindData = (d?.eval_summary ?? []).map((k) => ({
    name: KIND_LABEL[k.kind] ?? k.kind,
    value: k.avg_score ?? 0,
    runs: k.runs,
  }));
  const totalRuns = (d?.eval_summary ?? []).reduce((a, k) => a + k.runs, 0);

  return (
    <div>
      <PageHeader
        eyebrow="Insights"
        title="Insights"
        description="Evaluation effectiveness, marketplace activity and graph shape at a glance."
        actions={
          <Select
            placeholder="Select workspace"
            style={{ minWidth: 220 }}
            value={wsId}
            onChange={setActiveWs}
            options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
          />
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="Concepts" value={d?.graph?.concepts ?? 0} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="References" value={d?.graph?.references ?? 0} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="Eval runs" value={totalRuns} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="Orphans" value={d?.graph?.orphans?.length ?? 0} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Concept types">
            {typeData.length ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={typeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={tokens.color.line} />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {typeData.map((t) => (
                      <Cell key={t.name} fill={TYPE_COLOR[t.name] ?? tokens.color.ink2} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No concepts" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Average eval score by kind">
            {kindData.length ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={kindData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={tokens.color.line} />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#E82127" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="No evaluations yet — run some from a concept's eval tabs"
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Most installed">
            <Table
              rowKey={(_, i) => String(i)}
              size="small"
              pagination={false}
              dataSource={d?.most_installed ?? []}
              locale={{ emptyText: "No installs yet" }}
              columns={[
                { title: "Skill", dataIndex: "title", key: "title" },
                {
                  title: "Type",
                  dataIndex: "type",
                  key: "type",
                  render: (t: string) => (t ? <Tag color={TYPE_COLOR[t]}>{t}</Tag> : null),
                  width: 100,
                },
                { title: "Installs", dataIndex: "downloads", key: "downloads", width: 90 },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Hubs (most connected)">
            <Table
              rowKey={(_, i) => String(i)}
              size="small"
              pagination={false}
              dataSource={d?.graph?.hubs ?? []}
              locale={{ emptyText: "No concepts" }}
              columns={[
                { title: "Concept", dataIndex: "title", key: "title" },
                { title: "Links", dataIndex: "degree", key: "degree", width: 80 },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24}>
          <Card title="Recent evaluations">
            <Table
              rowKey={(_, i) => String(i)}
              size="small"
              pagination={false}
              dataSource={d?.eval_recent ?? []}
              locale={{ emptyText: "No evaluations yet" }}
              columns={[
                { title: "Concept", dataIndex: "concept_path", key: "concept_path", ellipsis: true },
                {
                  title: "Kind",
                  dataIndex: "kind",
                  key: "kind",
                  width: 110,
                  render: (k: string) => <Tag>{KIND_LABEL[k] ?? k}</Tag>,
                },
                {
                  title: "Score",
                  dataIndex: "score",
                  key: "score",
                  width: 80,
                  render: (s: number | null) => (s == null ? "—" : s),
                },
                { title: "Summary", dataIndex: "summary", key: "summary", ellipsis: true },
                {
                  title: "When",
                  dataIndex: "created_at",
                  key: "created_at",
                  width: 160,
                  render: (t: string | null) =>
                    t ? t.slice(0, 19).replace("T", " ") : "",
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
