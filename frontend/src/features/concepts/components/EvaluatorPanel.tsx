import { Alert, Button, Empty, List, Progress, Space, Tag, Typography } from "antd";
import { useEvaluateConcept, type EvalReport } from "../api/conceptApi";
import { tokens } from "@/app/theme/tokens";

const SEVERITY_COLOR: Record<string, string> = {
  error: tokens.color.bad,
  warning: tokens.color.warn,
  info: tokens.color.ink3,
};

export function EvaluatorPanel({ workspaceId, path }: { workspaceId: string; path: string }) {
  const evaluate = useEvaluateConcept(workspaceId, path);
  const report = evaluate.data as EvalReport | undefined;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%", maxWidth: 760 }}>
      <Space>
        <Button type="primary" loading={evaluate.isPending} onClick={() => evaluate.mutate()}>
          Run evaluation
        </Button>
        {report && (
          <Typography.Text type="secondary">
            Overall {report.overall_score} · confidence {Math.round(report.confidence * 100)}%
            {report.used_llm ? " · LLM-assisted" : " · rules-only"}
          </Typography.Text>
        )}
      </Space>

      {report && report.blocking_issues.length > 0 && (
        <Alert
          type="error"
          showIcon
          message="Blocking issues"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {report.blocking_issues.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          }
        />
      )}
      {report && report.blocking_issues.length === 0 && (
        <Alert type="success" showIcon message="No blocking issues" />
      )}

      {!report && !evaluate.isPending && (
        <Empty description="Run the six evaluators to score this concept" />
      )}

      {report && (
        <List
          dataSource={report.results}
          rowKey={(r) => r.evaluator}
          renderItem={(r) => (
            <List.Item style={{ display: "block" }}>
              <Space style={{ width: "100%", justifyContent: "space-between" }}>
                <Typography.Text strong style={{ textTransform: "capitalize" }}>
                  {r.evaluator}
                  {r.blocking && <Tag color="error" style={{ marginLeft: 8 }}>blocking</Tag>}
                  {r.used_llm && <Tag style={{ marginLeft: 4 }}>llm</Tag>}
                </Typography.Text>
                <Progress
                  percent={Math.round(r.score)}
                  size="small"
                  style={{ width: 160 }}
                  status={r.blocking ? "exception" : "normal"}
                />
              </Space>
              {r.findings.length > 0 && (
                <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                  {r.findings.map((f, i) => (
                    <li key={i} style={{ color: SEVERITY_COLOR[f.severity] ?? tokens.color.ink2 }}>
                      {f.message}
                      {f.evidence ? ` — ${f.evidence}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </List.Item>
          )}
        />
      )}
    </Space>
  );
}

export default EvaluatorPanel;
