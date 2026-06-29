import { Alert, Button, Empty, Space, Statistic, Table, Tag, Typography } from "antd";
import { useDeepEvaluateConcept, type DeepCase, type DeepEvalReport } from "../api/conceptApi";
import { tokens } from "@/app/theme/tokens";

export function DeepEvalPanel({ workspaceId, path }: { workspaceId: string; path: string }) {
  const deep = useDeepEvaluateConcept(workspaceId, path);
  const report = deep.data as DeepEvalReport | undefined;

  const columns = [
    {
      title: "Scenario",
      dataIndex: "scenario",
      key: "scenario",
      render: (s: string, r: DeepCase) => (
        <span>
          {r.is_edge_case && <Tag color="gold">edge</Tag>}
          {s}
        </span>
      ),
    },
    { title: "Without", dataIndex: "without_score", key: "without", width: 90 },
    { title: "With", dataIndex: "with_score", key: "with", width: 80 },
    {
      title: "Δ",
      dataIndex: "delta",
      key: "delta",
      width: 70,
      render: (d: number) => (
        <span style={{ color: d > 0 ? tokens.color.ok : d < 0 ? tokens.color.bad : tokens.color.ink3 }}>
          {d > 0 ? `+${d}` : d}
        </span>
      ),
    },
    { title: "Judge note", dataIndex: "note", key: "note" },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%", maxWidth: 900 }}>
      <div>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          Agentic evaluation: an LLM generates test cases and edge cases, answers each{" "}
          <b>with</b> and <b>without</b> this skill, then a judge scores them — measuring whether
          the skill actually improves results.
        </Typography.Paragraph>
        <Button type="primary" loading={deep.isPending} onClick={() => deep.mutate(5)}>
          Run deep evaluation
        </Button>
      </div>

      {report && !report.available && (
        <Alert type="warning" showIcon message="Deep evaluation unavailable" description={report.reason} />
      )}

      {report && report.available && report.cases.length > 0 && (
        <>
          <Alert
            type={report.effectiveness_avg > 0.5 ? "success" : "info"}
            showIcon
            message={report.summary}
          />
          <Space size="large" wrap>
            <Statistic title="Effectiveness (avg Δ)" value={report.effectiveness_avg} precision={2} />
            <Statistic title="Win rate" value={Math.round(report.win_rate * 100)} suffix="%" />
            <Statistic title="With skill (avg)" value={report.with_avg} precision={1} />
            <Statistic title="Without skill (avg)" value={report.without_avg} precision={1} />
          </Space>
          <Table<DeepCase>
            rowKey={(_, i) => String(i)}
            dataSource={report.cases}
            columns={columns}
            pagination={false}
            size="small"
          />
        </>
      )}

      {report && report.available && report.cases.length === 0 && (
        <Empty description="No usable test cases were produced — try again." />
      )}
    </Space>
  );
}

export default DeepEvalPanel;
