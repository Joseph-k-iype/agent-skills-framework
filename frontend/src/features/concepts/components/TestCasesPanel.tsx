import { BulbOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { Alert, Button, Empty, Input, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import {
  useEvalCases,
  useGradeEval,
  useSaveEvalCases,
  useSuggestEvalCases,
  type EvalCase,
  type GradeCaseResult,
  type GradeReport,
} from "../api/conceptApi";
import { tokens } from "@/app/theme/tokens";

export function TestCasesPanel({ workspaceId, path }: { workspaceId: string; path: string }) {
  const casesQuery = useEvalCases(workspaceId, path);
  const save = useSaveEvalCases(workspaceId, path);
  const suggest = useSuggestEvalCases(workspaceId, path);
  const grade = useGradeEval(workspaceId, path);

  const [rows, setRows] = useState<EvalCase[]>([]);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (casesQuery.data && !loaded) {
      setRows(casesQuery.data);
      setLoaded(true);
    }
  }, [casesQuery.data, loaded]);

  const report = grade.data as GradeReport | undefined;

  const update = (i: number, field: keyof EvalCase, value: string) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)));
  const remove = (i: number) => setRows((rs) => rs.filter((_, idx) => idx !== i));
  const addRow = () => setRows((rs) => [...rs, { input: "", expected: "" }]);

  const onSuggest = () =>
    suggest.mutate(5, { onSuccess: (drafts) => setRows((rs) => [...rs, ...drafts]) });

  const onSave = () => save.mutate(rows, { onSuccess: () => message.success("Test cases saved") });

  const onRun = () => {
    const usable = rows.filter((r) => r.input.trim());
    if (!usable.length) {
      message.warning("Add at least one case with an input");
      return;
    }
    grade.mutate(usable);
  };

  const editorColumns = [
    {
      title: "Input",
      dataIndex: "input",
      key: "input",
      render: (_: string, _r: EvalCase, i: number) => (
        <Input.TextArea
          autoSize={{ minRows: 2, maxRows: 8 }}
          placeholder="What the user sends to the skill…"
          value={rows[i]?.input}
          onChange={(e) => update(i, "input", e.target.value)}
        />
      ),
    },
    {
      title: "Expected output",
      dataIndex: "expected",
      key: "expected",
      render: (_: string, _r: EvalCase, i: number) => (
        <Input.TextArea
          autoSize={{ minRows: 2, maxRows: 8 }}
          placeholder="The correct answer (leave blank to fill later)…"
          value={rows[i]?.expected}
          onChange={(e) => update(i, "expected", e.target.value)}
        />
      ),
    },
    {
      title: "",
      key: "actions",
      width: 44,
      render: (_: unknown, _r: EvalCase, i: number) => (
        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(i)} />
      ),
    },
  ];

  const resultColumns = [
    { title: "Input", dataIndex: "input", key: "input", width: 200, ellipsis: true },
    { title: "Expected", dataIndex: "expected", key: "expected", width: 180, ellipsis: true },
    { title: "Actual", dataIndex: "actual", key: "actual", ellipsis: true },
    {
      title: "Score",
      dataIndex: "score",
      key: "score",
      width: 80,
      render: (s: number) => `${s}/10`,
    },
    {
      title: "Result",
      dataIndex: "passed",
      key: "passed",
      width: 90,
      render: (p: boolean) => <Tag color={p ? "success" : "error"}>{p ? "pass" : "fail"}</Tag>,
    },
    { title: "Why", dataIndex: "reasoning", key: "reasoning", ellipsis: true },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%", maxWidth: 980 }}>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Provide test scenarios as <b>input</b> + <b>expected output</b>. The skill runs on each
        input and a judge grades the actual output against your expected one. Cases are saved with
        the skill (versioned), so they double as a regression suite.
      </Typography.Paragraph>

      <Space wrap>
        <Button icon={<BulbOutlined />} loading={suggest.isPending} onClick={onSuggest}>
          Suggest cases
        </Button>
        <Button icon={<PlusOutlined />} onClick={addRow}>
          Add row
        </Button>
        <Button onClick={onSave} loading={save.isPending} disabled={!rows.length}>
          Save
        </Button>
        <Button type="primary" onClick={onRun} loading={grade.isPending} disabled={!rows.length}>
          Run {rows.filter((r) => r.input.trim()).length || ""} scenarios
        </Button>
      </Space>

      {suggest.isError && (
        <Alert
          type="error"
          showIcon
          message="Couldn't draft cases"
          description={(suggest.error as Error)?.message}
        />
      )}
      {grade.isError && (
        <Alert
          type="error"
          showIcon
          message="Evaluation failed"
          description={(grade.error as Error)?.message}
        />
      )}

      {rows.length === 0 ? (
        <Empty description="No test cases yet — Suggest cases or Add a row to begin" />
      ) : (
        <Table<EvalCase>
          rowKey={(_, i) => String(i)}
          dataSource={rows}
          columns={editorColumns}
          pagination={false}
          size="small"
        />
      )}

      {report && !report.available && (
        <Alert type="warning" showIcon message="Evaluation unavailable" description={report.reason} />
      )}

      {report && report.available && (
        <>
          <Alert
            type={report.pass_rate >= 0.7 ? "success" : "info"}
            showIcon
            message={report.summary}
          />
          {report.missing_expected > 0 && (
            <Alert
              type="warning"
              showIcon
              message={`${report.missing_expected} case(s) had no expected output and were not graded`}
              description="Fill in the expected output for those rows to include them."
            />
          )}
          <Space size="large" wrap>
            <Statistic
              title="Pass rate"
              value={Math.round(report.pass_rate * 100)}
              suffix="%"
              valueStyle={{ color: report.pass_rate >= 0.7 ? tokens.color.ok : tokens.color.warn }}
            />
            <Statistic title="Avg score" value={report.avg_score} precision={2} suffix="/10" />
            <Statistic title="Graded" value={report.cases.length} />
          </Space>
          {report.cases.length > 0 && (
            <Table<GradeCaseResult>
              rowKey={(_, i) => String(i)}
              dataSource={report.cases}
              columns={resultColumns}
              pagination={false}
              size="small"
            />
          )}
        </>
      )}
    </Space>
  );
}

export default TestCasesPanel;
