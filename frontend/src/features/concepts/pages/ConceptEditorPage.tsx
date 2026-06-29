import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import {
  App as AntApp,
  AutoComplete,
  Button,
  Form,
  Input,
  Select,
  Space,
  Spin,
  Steps,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import {
  useConcept,
  useConceptHistory,
  useUpdateConcept,
} from "../api/conceptApi";
import { MarkdownPreview } from "../components/MarkdownPreview";
import { EvaluatorPanel } from "../components/EvaluatorPanel";

// Free-text runtime — these are only suggestions; any value can be typed.
const RUNTIME_SUGGESTIONS = [
  "python 3.12",
  "node 20",
  "typescript",
  "bash",
  "claude-code",
  "langgraph",
  "container",
  "mcp",
].map((value) => ({ value }));

export default function ConceptEditorPage() {
  const params = useParams();
  const workspaceId = params.workspaceId ?? "";
  const path = params["*"] ?? "";
  const navigate = useNavigate();
  const { message } = AntApp.useApp();

  const concept = useConcept(workspaceId, path);
  const history = useConceptHistory(workspaceId, path);
  const update = useUpdateConcept(workspaceId, path);

  const [form] = Form.useForm();
  const [body, setBody] = useState("");

  useEffect(() => {
    if (concept.data) {
      form.setFieldsValue({
        title: concept.data.title,
        type: concept.data.type,
        description: concept.data.description,
        runtime: concept.data.runtime,
        tags: concept.data.tags,
        capabilities: concept.data.capabilities,
      });
      setBody(concept.data.body);
    }
  }, [concept.data, form]);

  if (concept.isLoading || !concept.data) {
    return <Spin style={{ marginTop: 120, display: "block" }} />;
  }
  const c = concept.data;

  async function save() {
    const v = await form.validateFields();
    await update.mutateAsync({ ...v, body });
    message.success("Saved");
  }

  const editorTab = (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, minHeight: 420 }}>
      <div>
        <Typography.Text type="secondary">Markdown body</Typography.Text>
        <Input.TextArea
          aria-label="Concept body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          autoSize={{ minRows: 18, maxRows: 40 }}
          style={{ fontFamily: tokens.font.mono, marginTop: 6 }}
          placeholder={"# Title\n\nWrite the skill here. Draw diagrams:\n\n```mermaid\nflowchart LR\n  A --> B\n```"}
        />
      </div>
      <div>
        <Typography.Text type="secondary">Preview</Typography.Text>
        <div
          style={{
            marginTop: 6,
            border: `1px solid ${tokens.color.line}`,
            borderRadius: tokens.radius,
            padding: 16,
            background: tokens.color.surface,
            overflow: "auto",
          }}
        >
          <MarkdownPreview source={body} />
        </div>
      </div>
    </div>
  );

  const metadataTab = (
    <Space direction="vertical" size="large" style={{ width: "100%", maxWidth: 560 }}>
      <Form.Item label="Title" name="title" rules={[{ required: true }]}>
        <Input size="large" />
      </Form.Item>
      <Form.Item label="Type" name="type" tooltip="Free text — e.g. skill, agent, prompt, doc">
        <Input placeholder="skill" />
      </Form.Item>
      <Form.Item label="Description" name="description">
        <Input.TextArea rows={3} placeholder="One-sentence summary" />
      </Form.Item>
      <Form.Item label="Runtime" name="runtime" tooltip="Free text — type anything">
        <AutoComplete
          options={RUNTIME_SUGGESTIONS}
          placeholder="e.g. python 3.12, rust 1.79, claude-code"
          filterOption={(input, option) =>
            (option?.value ?? "").toLowerCase().includes(input.toLowerCase())
          }
          allowClear
        />
      </Form.Item>
      <Form.Item label="Tags" name="tags">
        <Select mode="tags" placeholder="Add tags" tokenSeparators={[","]} />
      </Form.Item>
      <Form.Item label="Capabilities" name="capabilities">
        <Select mode="tags" placeholder="e.g. extraction:invoice" tokenSeparators={[","]} />
      </Form.Item>
    </Space>
  );

  const linkedTab = (
    <div style={{ maxWidth: 560 }}>
      <Typography.Paragraph type="secondary">
        These links are derived from markdown links in the body — they are the graph edges.
      </Typography.Paragraph>
      {c.references.length === 0 ? (
        <Typography.Text type="secondary">No linked concepts yet.</Typography.Text>
      ) : (
        <Space direction="vertical">
          {c.references.map((r) => (
            <Tag
              key={r.path}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/concepts/${workspaceId}/${r.path}`)}
            >
              {r.title ?? r.path}
            </Tag>
          ))}
        </Space>
      )}
    </div>
  );

  const historyTab = (
    <Steps
      direction="vertical"
      size="small"
      current={-1}
      items={(history.data ?? []).map((h) => ({
        title: h.message,
        description: `${h.author} · ${h.ts.slice(0, 19).replace("T", " ")}`,
      }))}
    />
  );

  const tabs = [
    { key: "editor", label: "Editor", children: editorTab },
    { key: "metadata", label: "Metadata", children: metadataTab },
    { key: "linked", label: "Linked concepts", children: linkedTab },
    {
      key: "evaluate",
      label: "Evaluate",
      children: <EvaluatorPanel workspaceId={workspaceId} path={path} />,
    },
    { key: "history", label: "History", children: historyTab },
  ];

  return (
    <div style={{ paddingBottom: 80 }}>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/workspace")}
        style={{ marginBottom: 8 }}
      >
        Workspace
      </Button>
      <PageHeader
        eyebrow={`${c.type}${c.runtime ? ` · ${c.runtime}` : ""}`}
        title={c.title}
        description={c.path}
      />
      <Form form={form} layout="vertical">
        <Tabs items={tabs} />
      </Form>

      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          background: tokens.color.surface,
          borderTop: `1px solid ${tokens.color.line}`,
          padding: "12px 28px",
          display: "flex",
          justifyContent: "flex-end",
          gap: 12,
          zIndex: 20,
        }}
      >
        <Button type="primary" icon={<SaveOutlined />} loading={update.isPending} onClick={save}>
          Save
        </Button>
      </div>
    </div>
  );
}
