import { Button, Descriptions, Empty, Popconfirm, Space, Typography } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import type { Folder, Workspace } from "../api/workspaceApi";
import { tokens } from "@/app/theme/tokens";

interface Props {
  workspace: Workspace;
  folder: Folder | null;
  onDelete: (id: string) => void;
}

export function AssetDetailPanel({ workspace, folder, onDelete }: Props) {
  if (!folder) {
    return (
      <div style={{ paddingTop: 64 }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Select a folder to see details" />
      </div>
    );
  }
  return (
    <div>
      <Space style={{ width: "100%", justifyContent: "space-between" }} align="start">
        <div>
          <div style={{ fontSize: 12, letterSpacing: "0.14em", color: tokens.color.ink3, textTransform: "uppercase" }}>
            Folder
          </div>
          <Typography.Title level={4} style={{ margin: "4px 0 0" }}>
            {folder.name}
          </Typography.Title>
        </div>
        <Popconfirm
          title="Delete folder"
          description="This removes the folder and everything inside it."
          okText="Delete"
          okButtonProps={{ danger: true }}
          onConfirm={() => onDelete(folder.id)}
        >
          <Button danger type="text" icon={<DeleteOutlined />}>
            Delete
          </Button>
        </Popconfirm>
      </Space>
      <Descriptions column={1} style={{ marginTop: 20 }} size="small">
        <Descriptions.Item label="Path">
          <Typography.Text code>{folder.path}</Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Workspace">{workspace.name}</Descriptions.Item>
        <Descriptions.Item label="Status">{folder.status}</Descriptions.Item>
        <Descriptions.Item label="ID">
          <Typography.Text type="secondary" copyable>
            {folder.id}
          </Typography.Text>
        </Descriptions.Item>
      </Descriptions>
    </div>
  );
}
