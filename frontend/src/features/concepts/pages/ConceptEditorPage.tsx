import { ArrowLeftOutlined, LinkOutlined, SaveOutlined } from "@ant-design/icons";
import {
  App as AntApp,
  AutoComplete,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Spin,
  Steps,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import {
  useConcept,
  useConcepts,
  useConceptHistory,
  useUpdateConcept,
} from "../api/conceptApi";
import { MarkdownPreview } from "../components/MarkdownPreview";
import { EvaluatorPanel } from "../components/EvaluatorPanel";
import { DeepEvalPanel } from "../components/DeepEvalPanel";

export default function ConceptEditorPage() {
  const params = useParams();
  const workspaceId = params.workspaceId ?? "";
  const path = params["*"] ?? "";
  const navigate = useNavigate();
  const { message } = AntApp.useApp();

  const concept = useConcept(workspaceId, path);
  const concepts = useConcepts(workspaceId);
  const history = useConceptHistory(workspaceId, path);
  const update = useUpdateConcept(workspaceId, path);

  const [form] = Form.useForm();
  const [body, setBody] = useState("");
  const [linkOpen, setLinkOpen] = useState(false);
  const cursorRef = useRef<number | null>(null);

  // Runtime suggestions are the distinct runtimes already in use — not hardcoded.
  const runtimeOptions = useMemo(() => {
    const seen = new Set<string>();
    for (const c of concepts.data ?? []) {
      if (c.runtime) seen.add(c.runtime);
    }
    return Array.from(seen).sort().map((value) => ({ value }));
  }, [concepts.data]);

  // Other concepts in this workspace, available to link to.
  const linkTargets = useMemo(
    () => (concepts.data ?? []).filter((c) => c.path !== path),
    [concepts.data, path],
  );

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

  function insertLink(targetPath: string, title: string) {
    // Bundle-root markdown link — resolves regardless of where this file lives.
    const snippet = `[${title}](/${targetPath})`;
    const at = cursorRef.current ?? body.length;
    const next = body.slice(0, at) + snippet + body.slice(at);
    setBody(next);
    cursorRef.current = at + snippet.length;
    setLinkOpen(false);
    message.success("Link inserted — it becomes a graph edge on save");
  }

  const editorTab = (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, minHeight: 420 }}>
      <div>
        <Space style={{ justifyContent: "space-between", width: "100%" }}>
          <Typography.Text type="secondary">Markdown body</Typography.Text>
          <Button size="small" icon={<LinkOutlined />} onClick={() => setLinkOpen(true)}>
            Insert link
          </Button>
        </Space>
        <Input.TextArea
          aria-label="Concept body"
          value={body}
          onChange={(e) => {
            setBody(e.target.value);
            cursorRef.current = e.target.selectionStart;
          }}
          onSelect={(e) => {
            cursorRef.current = (e.target as HTMLTextAreaElement).selectionStart;
          }}
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
      <Form.Item
        label="Runtime"
        name="runtime"
        tooltip="Free text — pick one already in use or type a new one"
      >
        <AutoComplete
          options={runtimeOptions}
          placeholder="type anything — e.g. python 3.12, rust 1.79, claude-code"
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
        These links are derived from markdown links in the body — they are the graph edges. Use
        “Insert link” in the editor to add more.
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
    {
      key: "deep",
      label: "Deep eval",
      children: <DeepEvalPanel workspaceId={workspaceId} path={path} />,
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

      <Modal
        title="Insert a link to another concept"
        open={linkOpen}
        footer={null}
        onCancel={() => setLinkOpen(false)}
      >
        <Typography.Paragraph type="secondary">
          Pick a concept in this workspace. A markdown link is inserted at your cursor — on save it
          becomes a graph edge and shows under “Linked concepts”.
        </Typography.Paragraph>
        <Select
          showSearch
          autoFocus
          style={{ width: "100%" }}
          placeholder="Search concepts to link…"
          optionFilterProp="label"
          loading={concepts.isLoading}
          notFoundContent={linkTargets.length === 0 ? "No other concepts yet" : "No match"}
          onSelect={(value: string) => {
            const target = linkTargets.find((t) => t.path === value);
            if (target) insertLink(target.path, target.title);
          }}
          options={linkTargets.map((t) => ({
            value: t.path,
            label: `${t.title} — ${t.path}`,
          }))}
        />
      </Modal>
    </div>
  );
}
