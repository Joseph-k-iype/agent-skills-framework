import { App as AntApp, Button, Form, Input, Modal, Select } from "antd";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkspaces } from "@/features/workspace/api/workspaceApi";
import { useAuthStore } from "@/stores/authStore";
import { useCloneListing, type CloneResult } from "../api/marketplaceApi";
import type { VersionRef } from "../api/publicMarketplaceApi";

interface CloneModalProps {
  open: boolean;
  listingId: string;
  listingTitle: string;
  versions: VersionRef[];
  onClose: () => void;
}

interface FormValues {
  workspace_id: string;
  folder_path?: string;
  name?: string;
  version?: number;
}

export function CloneModal({ open, listingId, listingTitle, versions, onClose }: CloneModalProps) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const { message } = AntApp.useApp();
  const [form] = Form.useForm<FormValues>();
  const workspaces = useWorkspaces();
  const clone = useCloneListing(listingId);

  // Unauthenticated users can't clone — bounce to login preserving return path.
  useEffect(() => {
    if (open && !user) {
      navigate(`/login?next=/marketplace/${listingId}`);
    }
  }, [open, user, listingId, navigate]);

  if (!user) return null;

  const submit = () => {
    form
      .validateFields()
      .then((values) => {
        clone.mutate(
          {
            workspace_id: values.workspace_id,
            folder_path: values.folder_path || undefined,
            name: values.name || undefined,
            version: values.version,
          },
          {
            onSuccess: (result: CloneResult) => {
              message.success(`Cloned to ${result.workspace_id}/${result.path}`);
              onClose();
            },
            onError: (e: unknown) => {
              const msg = e instanceof Error ? e.message : "Clone failed";
              message.error(msg);
            },
          },
        );
      })
      .catch(() => {});
  };

  return (
    <Modal
      open={open}
      title={`Clone “${listingTitle}” to a workspace`}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Cancel
        </Button>,
        <Button key="clone" type="primary" loading={clone.isPending} onClick={submit}>
          Clone
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical" initialValues={{ folder_path: "", name: listingTitle }}>
        <Form.Item
          name="workspace_id"
          label="Workspace"
          rules={[{ required: true, message: "Pick a workspace" }]}
        >
          <Select
            aria-label="Workspace"
            placeholder="Select a workspace"
            options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
          />
        </Form.Item>
        <Form.Item name="folder_path" label="Folder path (optional)">
          <Input placeholder="e.g. imported/" />
        </Form.Item>
        <Form.Item name="name" label="Name">
          <Input placeholder={listingTitle} />
        </Form.Item>
        {versions.length > 0 && (
          <Form.Item name="version" label="Version">
            <Select
              allowClear
              placeholder="Latest"
              options={versions.map((v) => ({ value: v.version, label: `v${v.version}` }))}
            />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
