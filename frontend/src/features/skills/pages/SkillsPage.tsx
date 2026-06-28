import { PlusOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Form, Input, Modal, Select, Space, Table, Tag } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { useWorkspaces, useWorkspaceTree } from "@/features/workspace/api/workspaceApi";
import { useCreateSkill, useSkills, type Skill } from "../api/skillApi";

const STATUS_COLOR: Record<string, string> = { draft: "default", published: "green" };

export default function SkillsPage() {
  const navigate = useNavigate();
  const { message } = AntApp.useApp();
  const skills = useSkills();
  const workspaces = useWorkspaces();
  const createSkill = useCreateSkill();

  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const wsId = Form.useWatch("workspace_id", form);
  const tree = useWorkspaceTree(wsId);

  async function submit() {
    const v = await form.validateFields();
    await createSkill.mutateAsync({
      name: v.name,
      folder_id: v.folder_id,
      workspace_id: v.workspace_id,
      runtime: v.runtime,
    });
    message.success("Skill created");
    setOpen(false);
    form.resetFields();
  }

  const columns = [
    { title: "Name", dataIndex: "name", key: "name", render: (t: string) => <strong>{t}</strong> },
    { title: "Version", dataIndex: "version", key: "version", width: 110 },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 130,
      render: (s: string) => <Tag color={STATUS_COLOR[s] ?? "default"}>{s}</Tag>,
    },
    { title: "Runtime", dataIndex: "runtime", key: "runtime", width: 120 },
    {
      title: "Capabilities",
      dataIndex: "capabilities",
      key: "capabilities",
      render: (caps: string[]) => (
        <Space size={[4, 4]} wrap>
          {caps.slice(0, 3).map((c) => (
            <Tag key={c} bordered={false}>
              {c}
            </Tag>
          ))}
          {caps.length > 3 && <Tag bordered={false}>+{caps.length - 3}</Tag>}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        eyebrow="Skills"
        title="Skills"
        description="Author, version and publish AI agent skills."
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
            New skill
          </Button>
        }
      />
      <Table<Skill>
        rowKey="id"
        loading={skills.isLoading}
        dataSource={skills.data ?? []}
        columns={columns}
        onRow={(r) => ({ onClick: () => navigate(`/skills/${r.id}`), style: { cursor: "pointer" } })}
        pagination={false}
      />

      <Modal title="New skill" open={open} onCancel={() => setOpen(false)} onOk={submit} okText="Create" confirmLoading={createSkill.isPending}>
        <Form form={form} layout="vertical" requiredMark={false} initialValues={{ runtime: "python" }}>
          <Form.Item label="Name" name="name" rules={[{ required: true }]}>
            <Input placeholder="e.g. Revenue Reporter" />
          </Form.Item>
          <Form.Item label="Workspace" name="workspace_id" rules={[{ required: true }]}>
            <Select
              placeholder="Select workspace"
              options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
            />
          </Form.Item>
          <Form.Item label="Folder" name="folder_id" rules={[{ required: true }]}>
            <Select
              placeholder={wsId ? "Select folder" : "Select a workspace first"}
              disabled={!wsId}
              options={(tree.data?.folders ?? []).map((f) => ({ value: f.id, label: f.path ?? f.name }))}
            />
          </Form.Item>
          <Form.Item label="Runtime" name="runtime">
            <Select options={[{ value: "python" }, { value: "typescript" }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
