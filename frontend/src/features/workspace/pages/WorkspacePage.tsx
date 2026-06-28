import { FolderAddOutlined, PlusOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Col, Empty, Input, Modal, Row, Select, Space, Tree, Typography } from "antd";
import type { TreeProps } from "antd";
import { useMemo, useState } from "react";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { AssetDetailPanel } from "../components/AssetDetailPanel";
import { buildTree } from "../components/buildTree";
import {
  useCreateFolder,
  useCreateWorkspace,
  useDeleteFolder,
  useMoveFolder,
  useWorkspaces,
  useWorkspaceTree,
} from "../api/workspaceApi";

export default function WorkspacePage() {
  const { message } = AntApp.useApp();
  const workspaces = useWorkspaces();
  const [activeWs, setActiveWs] = useState<string | undefined>();
  const wsId = activeWs ?? workspaces.data?.[0]?.id;
  const tree = useWorkspaceTree(wsId);
  const [selected, setSelected] = useState<string | null>(null);

  const createWs = useCreateWorkspace();
  const createFolder = useCreateFolder(wsId ?? "");
  const moveFolder = useMoveFolder(wsId ?? "");
  const deleteFolder = useDeleteFolder(wsId ?? "");

  const [wsModal, setWsModal] = useState(false);
  const [folderModal, setFolderModal] = useState(false);
  const [newName, setNewName] = useState("");

  const treeData = useMemo(
    () => (tree.data ? buildTree(tree.data.folders, tree.data.workspace.id) : []),
    [tree.data],
  );
  const selectedFolder = tree.data?.folders.find((f) => f.id === selected) ?? null;

  const onDrop: TreeProps["onDrop"] = (info) => {
    const dragId = String(info.dragNode.key);
    // Drop onto a node => into that folder; drop into root gap => workspace root.
    const newParent = info.dropToGap ? (wsId ?? "") : String(info.node.key);
    if (!newParent || newParent === dragId) return;
    moveFolder.mutate(
      { id: dragId, new_parent_id: newParent },
      { onError: (e) => message.error((e as Error).message) },
    );
  };

  async function submitWorkspace() {
    if (!newName.trim()) return;
    await createWs.mutateAsync({ name: newName.trim() });
    setNewName("");
    setWsModal(false);
    message.success("Workspace created");
  }

  async function submitFolder() {
    if (!newName.trim() || !wsId) return;
    const parent = selectedFolder?.id ?? wsId; // create under selection, else root
    await createFolder.mutateAsync({ name: newName.trim(), parent_id: parent });
    setNewName("");
    setFolderModal(false);
    message.success("Folder created");
  }

  return (
    <div>
      <PageHeader
        eyebrow="Authoring"
        title="Workspace"
        description="Organize knowledge packages, folders and assets."
        actions={
          <Space>
            <Select
              placeholder="Select workspace"
              style={{ minWidth: 200 }}
              value={wsId}
              onChange={(v) => {
                setActiveWs(v);
                setSelected(null);
              }}
              options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
            />
            <Button icon={<PlusOutlined />} onClick={() => setWsModal(true)}>
              New workspace
            </Button>
          </Space>
        }
      />

      {!workspaces.isLoading && (workspaces.data?.length ?? 0) === 0 ? (
        <Empty description="No workspaces yet" style={{ marginTop: 80 }}>
          <Button type="primary" onClick={() => setWsModal(true)}>
            Create your first workspace
          </Button>
        </Empty>
      ) : (
        <Row gutter={16}>
          <Col xs={24} md={10} lg={9}>
            <Card
              styles={{ body: { padding: 16 } }}
              title="Folders"
              extra={
                <Button
                  size="small"
                  icon={<FolderAddOutlined />}
                  disabled={!wsId}
                  onClick={() => setFolderModal(true)}
                >
                  New folder
                </Button>
              }
            >
              {treeData.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No folders" />
              ) : (
                <Tree
                  treeData={treeData}
                  draggable
                  blockNode
                  defaultExpandAll
                  selectedKeys={selected ? [selected] : []}
                  onSelect={(keys) => setSelected(keys[0] ? String(keys[0]) : null)}
                  onDrop={onDrop}
                />
              )}
              <Typography.Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 12, color: tokens.color.ink3 }}>
                Drag folders to reorganize. New folders are created under the selected folder.
              </Typography.Text>
            </Card>
          </Col>
          <Col xs={24} md={14} lg={15}>
            <Card styles={{ body: { padding: 24 } }}>
              {tree.data && (
                <AssetDetailPanel
                  workspace={tree.data.workspace}
                  folder={selectedFolder}
                  onDelete={(id) => {
                    deleteFolder.mutate(id, {
                      onSuccess: () => {
                        setSelected(null);
                        message.success("Folder deleted");
                      },
                    });
                  }}
                />
              )}
            </Card>
          </Col>
        </Row>
      )}

      <Modal
        title="New workspace"
        open={wsModal}
        onCancel={() => setWsModal(false)}
        onOk={submitWorkspace}
        okText="Create"
        confirmLoading={createWs.isPending}
      >
        <Input placeholder="Workspace name" value={newName} onChange={(e) => setNewName(e.target.value)} onPressEnter={submitWorkspace} />
      </Modal>
      <Modal
        title={selectedFolder ? `New folder in "${selectedFolder.name}"` : "New top-level folder"}
        open={folderModal}
        onCancel={() => setFolderModal(false)}
        onOk={submitFolder}
        okText="Create"
        confirmLoading={createFolder.isPending}
      >
        <Input placeholder="Folder name" value={newName} onChange={(e) => setNewName(e.target.value)} onPressEnter={submitFolder} />
      </Modal>
    </div>
  );
}
