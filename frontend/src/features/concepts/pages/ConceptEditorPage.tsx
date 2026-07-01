import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import {
  App as AntApp,
  AutoComplete,
  Button,
  Form,
  Input,
  Modal,
  Segmented,
  Select,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { useConcept, useConcepts, useUpdateConcept } from "../api/conceptApi";
import { MarkdownPreview } from "../components/MarkdownPreview";
import { EvaluatorPanel } from "../components/EvaluatorPanel";
import { DeepEvalPanel } from "../components/DeepEvalPanel";
import { TestCasesPanel } from "../components/TestCasesPanel";
import { VersionManager } from "../components/VersionManager";
import { TaxonomyPicker } from "../components/TaxonomyPicker";
import { ParentConceptSelect } from "../components/ParentConceptSelect";
import type { SkillEditorHandle } from "../components/editor/SkillEditor";
import { EditorToolbar } from "../components/editor/EditorToolbar";
import type { Transform } from "../lib/markdownTransforms";
import { NumberTicker } from "@/features/shared/fancy/NumberTicker";
import { SaveFlash } from "@/features/shared/fancy/SaveFlash";

const SkillEditor = lazy(() =>
  import("../components/editor/SkillEditor").then((m) => ({ default: m.SkillEditor })),
);

export default function ConceptEditorPage() {
  const params = useParams();
  const workspaceId = params.workspaceId ?? "";
  const path = params["*"] ?? "";
  const navigate = useNavigate();
  const { message } = AntApp.useApp();

  const concept = useConcept(workspaceId, path);
  const concepts = useConcepts(workspaceId);
  const update = useUpdateConcept(workspaceId, path);

  const [form] = Form.useForm();
  const [body, setBody] = useState("");
  const [linkOpen, setLinkOpen] = useState(false);
  const cursorRef = useRef<number | null>(null);
  const [mode, setMode] = useState<"edit" | "split" | "preview">("split");
  const [saved, setSaved] = useState(false);
  const editorRef = useRef<SkillEditorHandle>(null);

  const applyTransform = (t: Transform) => editorRef.current?.applyTransform(t);

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
        sources: concept.data.sources ?? [],
        parent_path: concept.data.parent_path ?? null,
      });
      setBody(concept.data.body);
    }
  }, [concept.data, form]);

  if (concept.isLoading || !concept.data) {
    return <Spin style={{ marginTop: 120, display: "block" }} />;
  }
  const c = concept.data;

  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;

  async function save() {
    const v = await form.validateFields();
    await update.mutateAsync({ ...v, body });
    message.success("Saved");
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
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

  const showEditor = mode !== "preview";
  const showPreview = mode !== "edit";
  const editorTab = (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Segmented
          size="small"
          value={mode}
          onChange={(v) => setMode(v as typeof mode)}
          options={[
            { label: "Edit", value: "edit" },
            { label: "Split", value: "split" },
            { label: "Preview", value: "preview" },
          ]}
        />
        <Space size={16}>
          <SaveFlash show={saved} />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            <NumberTicker value={wordCount} /> words
          </Typography.Text>
        </Space>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: mode === "split" ? "1fr 1fr" : "1fr",
          gap: 20,
          minHeight: 460,
        }}
      >
        {showEditor && (
          <div
            style={{
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              minHeight: 460,
            }}
          >
            <EditorToolbar onApply={applyTransform} onInsertConceptLink={() => setLinkOpen(true)} />
            <div style={{ flex: 1, minHeight: 400 }}>
              <Suspense fallback={<Spin style={{ margin: 40 }} />}>
                <SkillEditor ref={editorRef} value={body} onChange={setBody} />
              </Suspense>
            </div>
          </div>
        )}
        {showPreview && (
          <div
            style={{
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              padding: 16,
              background: tokens.color.surface,
              overflow: "auto",
            }}
          >
            <MarkdownPreview source={body} />
          </div>
        )}
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
        <TaxonomyPicker kind="capability" />
      </Form.Item>
      <Form.Item label="Sources" name="sources">
        <TaxonomyPicker kind="source" />
      </Form.Item>
      <Form.Item label="Parent concept" name="parent_path" tooltip="Optional — sets the concept's parent in the hierarchy">
        <ParentConceptSelect />
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

  const historyTab = <VersionManager workspaceId={workspaceId} path={path} />;

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
    {
      key: "testcases",
      label: "Test cases",
      children: <TestCasesPanel workspaceId={workspaceId} path={path} />,
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
