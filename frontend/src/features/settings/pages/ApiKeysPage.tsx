import { CopyOutlined, KeyOutlined, PlusOutlined } from "@ant-design/icons";
import { Alert, Button, Empty, Input, Modal, Popconfirm, Space, Table, Typography, message } from "antd";
import { useState } from "react";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { useApiKeys, useCreateApiKey, useRevokeApiKey, type ApiKey } from "../api/apiKeysApi";
import { KeyUsagePanel } from "../components/KeyUsagePanel";

export default function ApiKeysPage() {
  const keys = useApiKeys();
  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();

  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);

  const onCreate = () => {
    if (!name.trim()) {
      message.warning("Name your key");
      return;
    }
    create.mutate(name.trim(), {
      onSuccess: (k) => {
        setNewKey(k.key);
        setCreating(false);
        setName("");
      },
      onError: (e) => message.error((e as Error)?.message ?? "Couldn't create key"),
    });
  };

  return (
    <div>
      <PageHeader
        eyebrow="Settings"
        title="API Keys"
        description="Keys authenticate the EAKSO SDK and programmatic access. Treat them like passwords."
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>
            Create key
          </Button>
        }
      />

      <Table<ApiKey>
        rowKey="id"
        loading={keys.isLoading}
        dataSource={keys.data ?? []}
        locale={{ emptyText: <Empty description="No API keys yet — create one to use the SDK" /> }}
        pagination={false}
        expandable={{
          expandedRowRender: (record: ApiKey) => <KeyUsagePanel keyId={record.id} />,
          rowExpandable: () => true,
        }}
        columns={[
          { title: "Name", dataIndex: "name", key: "name" },
          {
            title: "Key",
            dataIndex: "prefix",
            key: "prefix",
            render: (p: string) => (
              <code style={{ fontFamily: tokens.font.mono }}>{p}…</code>
            ),
          },
          {
            title: "Last used",
            dataIndex: "last_used_at",
            key: "last_used_at",
            render: (t: string | null) => (t ? t.slice(0, 10) : "never"),
          },
          {
            title: "Created",
            dataIndex: "created_at",
            key: "created_at",
            render: (t: string | null) => (t ? t.slice(0, 10) : ""),
          },
          {
            title: "",
            key: "actions",
            width: 90,
            render: (_: unknown, r: ApiKey) => (
              <Popconfirm
                title="Revoke this key?"
                description="Any SDK or app using it will stop working immediately."
                okText="Revoke"
                okButtonProps={{ danger: true }}
                onConfirm={() =>
                  revoke.mutate(r.id, { onSuccess: () => message.success("Key revoked") })
                }
              >
                <Button size="small" danger>
                  Revoke
                </Button>
              </Popconfirm>
            ),
          },
        ]}
      />

      {/* Create modal */}
      <Modal
        open={creating}
        title="Create API key"
        okText="Create"
        confirmLoading={create.isPending}
        onOk={onCreate}
        onCancel={() => setCreating(false)}
      >
        <Typography.Paragraph type="secondary">
          Give the key a name so you can recognise it later (e.g. "production", "my-laptop").
        </Typography.Paragraph>
        <Input
          autoFocus
          placeholder="Key name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onPressEnter={onCreate}
          prefix={<KeyOutlined style={{ color: tokens.color.ink3 }} />}
        />
      </Modal>

      {/* Show-once modal */}
      <Modal
        open={!!newKey}
        title="Copy your API key now"
        footer={<Button type="primary" onClick={() => setNewKey(null)}>Done</Button>}
        onCancel={() => setNewKey(null)}
      >
        <Alert
          type="warning"
          showIcon
          message="This is the only time the full key is shown."
          description="Store it somewhere safe. If you lose it, revoke it and create a new one."
          style={{ marginBottom: 16 }}
        />
        <Space.Compact style={{ width: "100%" }}>
          <Input
            readOnly
            value={newKey ?? ""}
            style={{ fontFamily: tokens.font.mono, fontSize: 13 }}
          />
          <Button
            icon={<CopyOutlined />}
            onClick={() =>
              navigator.clipboard?.writeText(newKey ?? "").then(() => message.success("Copied"))
            }
          >
            Copy
          </Button>
        </Space.Compact>
      </Modal>
    </div>
  );
}
