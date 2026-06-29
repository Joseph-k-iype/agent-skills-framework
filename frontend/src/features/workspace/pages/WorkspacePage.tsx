import { FileAddOutlined, FolderAddOutlined, PlusOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Col, Empty, Input, Modal, Row, Select, Space, Tree, Typography } from "antd";
import type { TreeProps } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { AssetDetailPanel } from "../components/AssetDetailPanel";
import { buildTree, isFileKey, pathFromKey, type ConceptNode } from "../components/buildTree";
import {
  useCreateFolder,
  useCreateWorkspace,
  useDeleteFolder,
  useMoveFolder,
  useWorkspaces,
  useWorkspaceTree,
} from "../api/workspaceApi";
import { useConcepts, useCreateConcept } from "@/features/concepts/api/conceptApi";

export default function WorkspacePage() {
  const { message } = AntApp.useApp();
  const navigate = useNavigate();
  const workspaces = useWorkspaces();
  const [activeWs, setActiveWs] = useState<string | undefined>();
  const wsId = activeWs ?? workspaces.data?.[0]?.id;
  const tree = useWorkspaceTree(wsId);
  const concepts = useConcepts(wsId);
  const [selected, setSelected] = useState<string | null>(null);

  const createWs = useCreateWorkspace();
  const createFolder = useCreateFolder(wsId ?? "");
  const moveFolder = useMoveFolder(wsId ?? "");
  const deleteFolder = useDeleteFolder(wsId ?? "");
  const createConcept = useCreateConcept(wsId ?? "");

  const [wsModal, setWsModal] = useState(false);
  const [folderModal, setFolderModal] = useState(false);
  const [conceptModal, setConceptModal] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("skill");

  const conceptNodes: ConceptNode[] = useMemo(
    () => (concepts.data ?? []).map((c) => ({ path: c.path, title: c.title, type: c.type })),
    [concepts.data],
  );

  const treeData = useMemo(
    () => (tree.data ? buildTree(tree.data.folders, conceptNodes, tree.data.workspace.id) : []),
    [tree.data, conceptNodes],
  );
  const selectedFolder = tree.data?.folders.find((f) => f.id === selected) ?? null;
  const selectedFolderPath = (selectedFolder?.path ?? "").replace(/^\//, "");

  const onSelect: TreeProps["onSelect"] = (keys) => {
    const key = keys[0] ? String(keys[0]) : null;
    if (key && isFileKey(key)) {
      navigate(`/concepts/${wsId}/${pathFromKey(key)}`);
      return;
    }
    setSelected(key);
  };

  const onDrop: TreeProps["onDrop"] = (info) => {
    const dragId = String(info.dragNode.key);
    if (isFileKey(dragId)) return; // file moves happen via the editor for now
    const newParent = info.dropToGap ? (wsId ?? "") : String(info.node.key);
    if (!newParent || newParent === dragId || isFileKey(newParent)) return;
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
    const parent = selectedFolder?.id ?? wsId;
    await createFolder.mutateAsync({ name: newName.trim(), parent_id: parent });
    setNewName("");
    setFolderModal(false);
    message.success("Folder created");
  }

  async function submitConcept() {
    if (!newName.trim() || !wsId) return;
    const created = await createConcept.mutateAsync({
      name: newName.trim(),
      folder_path: selectedFolderPath,
      type: newType.trim() || "skill",
      body: `# ${newName.trim()}\n\nDescribe this ${newType.trim() || "skill"} here.\n`,
    });
    setNewName("");
    setConceptModal(false);
    message.success("Concept created");
    navigate(`/concepts/${wsId}/${created.path}`);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Authoring"
        title="Workspace"
        description="Folders and markdown concepts — skills, agents, prompts, docs."
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
              title="Files & folders"
              extra={
                <Space>
                  <Button
                    size="small"
                    icon={<FolderAddOutlined />}
                    disabled={!wsId}
                    onClick={() => setFolderModal(true)}
                  >
                    Folder
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    icon={<FileAddOutlined />}
                    disabled={!wsId}
                    onClick={() => setConceptModal(true)}
                  >
                    Concept
                  </Button>
                </Space>
              }
            >
              {treeData.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Empty workspace" />
              ) : (
                <Tree
                  treeData={treeData}
                  draggable
                  blockNode
                  defaultExpandAll
                  selectedKeys={selected ? [selected] : []}
                  onSelect={onSelect}
                  onDrop={onDrop}
                />
              )}
              <Typography.Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 12, color: tokens.color.ink3 }}>
                Click a file to edit it. New folders/concepts are created under the selected folder.
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
      <Modal
        title={selectedFolder ? `New concept in "${selectedFolder.name}"` : "New concept at root"}
        open={conceptModal}
        onCancel={() => setConceptModal(false)}
        onOk={submitConcept}
        okText="Create"
        confirmLoading={createConcept.isPending}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input placeholder="Concept name" value={newName} onChange={(e) => setNewName(e.target.value)} onPressEnter={submitConcept} />
          <Input addonBefore="type" placeholder="skill, agent, prompt, doc…" value={newType} onChange={(e) => setNewType(e.target.value)} />
        </Space>
      </Modal>
    </div>
  );
}
