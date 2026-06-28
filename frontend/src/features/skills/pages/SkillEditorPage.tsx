import { ArrowLeftOutlined, CloudUploadOutlined, SaveOutlined } from "@ant-design/icons";
import {
  App as AntApp,
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
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { useDocuments } from "@/features/knowledge/api/knowledgeApi";
import { usePublishSkill, useSkill, useSkillVersions, useUpdateSkill } from "../api/skillApi";

export default function SkillEditorPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { message } = AntApp.useApp();
  const skill = useSkill(id);
  const versions = useSkillVersions(id);
  const docs = useDocuments();
  const update = useUpdateSkill(id);
  const publish = usePublishSkill(id);

  const [form] = Form.useForm();
  const [publishOpen, setPublishOpen] = useState(false);
  const [nextVersion, setNextVersion] = useState("");

  useEffect(() => {
    if (skill.data) {
      form.setFieldsValue({
        name: skill.data.name,
        description: skill.data.description,
        runtime: skill.data.runtime,
        tags: skill.data.tags,
        capabilities: skill.data.capabilities,
        references: skill.data.references.map((r) => r.id),
      });
    }
  }, [skill.data, form]);

  if (skill.isLoading || !skill.data) {
    return <Spin style={{ marginTop: 120, display: "block" }} />;
  }
  const s = skill.data;

  async function saveDraft() {
    const v = await form.validateFields();
    await update.mutateAsync(v);
    message.success("Saved");
  }

  async function doPublish() {
    await update.mutateAsync(await form.validateFields());
    await publish.mutateAsync(nextVersion ? { version: nextVersion } : {});
    message.success(nextVersion ? `Published ${nextVersion}` : "Published");
    setPublishOpen(false);
    if (nextVersion) {
      const fresh = await versions.refetch();
      const current = fresh.data?.versions.find((x) => x.is_current);
      if (current) navigate(`/skills/${current.id}`);
    }
  }

  const tabs = [
    {
      key: "overview",
      label: "Overview",
      children: (
        <Space direction="vertical" size="large" style={{ width: "100%", maxWidth: 640 }}>
          <Form.Item label="Name" name="name" rules={[{ required: true }]}>
            <Input size="large" />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input.TextArea rows={4} placeholder="What does this skill do?" />
          </Form.Item>
        </Space>
      ),
    },
    {
      key: "metadata",
      label: "Metadata",
      children: (
        <Form.Item label="Tags" name="tags" style={{ maxWidth: 640 }}>
          <Select mode="tags" placeholder="Add tags" tokenSeparators={[","]} />
        </Form.Item>
      ),
    },
    {
      key: "okf",
      label: "OKF References",
      children: (
        <div style={{ maxWidth: 640 }}>
          <Typography.Paragraph type="secondary">
            Skills reference enterprise knowledge — they never copy it.
          </Typography.Paragraph>
          <Form.Item name="references">
            <Select
              mode="multiple"
              placeholder="Attach OKF documents"
              loading={docs.isLoading}
              options={(docs.data ?? []).map((d) => ({ value: d.id, label: d.title }))}
              optionFilterProp="label"
            />
          </Form.Item>
        </div>
      ),
    },
    {
      key: "runtime",
      label: "Runtime",
      children: (
        <Form.Item label="Runtime" name="runtime" style={{ maxWidth: 320 }}>
          <Select options={[{ value: "python" }, { value: "typescript" }]} />
        </Form.Item>
      ),
    },
    {
      key: "capabilities",
      label: "Capabilities",
      children: (
        <Form.Item label="Capabilities" name="capabilities" style={{ maxWidth: 640 }}>
          <Select mode="tags" placeholder="e.g. reporting:revenue" tokenSeparators={[","]} />
        </Form.Item>
      ),
    },
    {
      key: "versions",
      label: "Versions",
      children: (
        <Steps
          direction="vertical"
          size="small"
          current={(versions.data?.versions.length ?? 1) - 1}
          items={(versions.data?.versions ?? []).map((v) => ({
            title: (
              <span>
                v{v.version} <Tag color={v.status === "published" ? "green" : "default"}>{v.status}</Tag>
                {v.is_current && <Tag bordered={false}>current</Tag>}
              </span>
            ),
            description: v.updated_at?.slice(0, 10),
          }))}
        />
      ),
    },
  ];

  return (
    <div style={{ paddingBottom: 80 }}>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate("/skills")} style={{ marginBottom: 8 }}>
        Skills
      </Button>
      <PageHeader
        eyebrow={`${s.runtime} · v${s.version}`}
        title={s.name}
        description={s.description ?? undefined}
        actions={<Tag color={s.status === "published" ? "green" : "default"}>{s.status}</Tag>}
      />
      <Form form={form} layout="vertical">
        <Tabs items={tabs} />
      </Form>

      {/* Sticky action bar */}
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
        <Button icon={<SaveOutlined />} loading={update.isPending} onClick={saveDraft}>
          Save draft
        </Button>
        <Button
          type="primary"
          icon={<CloudUploadOutlined />}
          loading={publish.isPending}
          onClick={() => {
            setNextVersion("");
            setPublishOpen(true);
          }}
        >
          Publish
        </Button>
      </div>

      <Modal title="Publish skill" open={publishOpen} onCancel={() => setPublishOpen(false)} onOk={doPublish} okText="Publish" confirmLoading={publish.isPending}>
        <Typography.Paragraph type="secondary">
          Publish the current version, or enter a higher semantic version to create a new one.
        </Typography.Paragraph>
        <Input
          placeholder={`New version (current: ${s.version}) — leave blank to publish in place`}
          value={nextVersion}
          onChange={(e) => setNextVersion(e.target.value)}
        />
      </Modal>
    </div>
  );
}
