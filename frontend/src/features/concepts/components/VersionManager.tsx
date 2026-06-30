import { Alert, Button, Checkbox, Modal, Popconfirm, Space, Spin, Tag, Typography, message } from "antd";
import { useState } from "react";
import {
  useConceptDiff,
  useConceptHistory,
  useConceptVersions,
  useRestoreVersion,
  useVersionContent,
  type VersionEntry,
} from "../api/conceptApi";
import { tokens } from "@/app/theme/tokens";

function DiffViewer({ diff }: { diff: string }) {
  if (!diff.trim()) return <Alert type="info" showIcon message="No differences between these versions." />;
  return (
    <pre
      style={{
        background: tokens.color.surface,
        border: `1px solid ${tokens.color.line}`,
        borderRadius: 8,
        padding: 12,
        fontSize: 12,
        overflowX: "auto",
        maxHeight: 380,
      }}
    >
      {diff.split("\n").map((line, i) => {
        const color = line.startsWith("+") && !line.startsWith("+++")
          ? tokens.color.ok
          : line.startsWith("-") && !line.startsWith("---")
            ? tokens.color.bad
            : line.startsWith("@@")
              ? tokens.color.ink3
              : tokens.color.ink2;
        return (
          <div key={i} style={{ color, whiteSpace: "pre-wrap" }}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export function VersionManager({ workspaceId, path }: { workspaceId: string; path: string }) {
  const history = useConceptHistory(workspaceId, path);
  const versions = useConceptVersions(workspaceId, path);
  const diff = useConceptDiff(workspaceId, path);
  const restore = useRestoreVersion(workspaceId, path);

  const [picked, setPicked] = useState<string[]>([]);
  const [previewRef, setPreviewRef] = useState<string | null>(null);
  const preview = useVersionContent(workspaceId, path, previewRef);

  const togglePick = (sha: string) =>
    setPicked((p) => (p.includes(sha) ? p.filter((s) => s !== sha) : [...p, sha].slice(-2)));

  const onDiff = () => {
    if (picked.length !== 2) return;
    // history is newest-first; diff older → newer for a forward-reading patch.
    diff.mutate({ a: picked[1], b: picked[0] });
  };

  const onRestore = (ref: string) =>
    restore.mutate(ref, {
      onSuccess: () => message.success("Restored as a new version"),
      onError: (e) => message.error((e as Error)?.message ?? "Restore failed"),
    });

  return (
    <Space direction="vertical" size="large" style={{ width: "100%", maxWidth: 820 }}>
      {versions.data && versions.data.length > 0 && (
        <div>
          <Typography.Text type="secondary">Published versions</Typography.Text>
          <div style={{ marginTop: 6 }}>
            <Space wrap>
              {versions.data.map((v) => (
                <Tag
                  key={v.tag}
                  color="blue"
                  style={{ cursor: "pointer" }}
                  onClick={() => setPreviewRef(v.tag)}
                  title={`Preview v${v.version}`}
                >
                  v{v.version}
                </Tag>
              ))}
            </Space>
          </div>
        </div>
      )}

      <div>
        <Space style={{ marginBottom: 8 }}>
          <Typography.Text type="secondary">
            History — tick two commits to compare
          </Typography.Text>
          <Button
            size="small"
            type="primary"
            disabled={picked.length !== 2}
            loading={diff.isPending}
            onClick={onDiff}
          >
            Diff selected
          </Button>
        </Space>

        <Space direction="vertical" size={4} style={{ width: "100%" }}>
          {(history.data ?? []).map((h: VersionEntry) => (
            <div
              key={h.sha}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 10px",
                border: `1px solid ${tokens.color.line}`,
                borderRadius: 8,
              }}
            >
              <Checkbox checked={picked.includes(h.sha)} onChange={() => togglePick(h.sha)} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>{h.message}</div>
                <div style={{ fontSize: 12, color: tokens.color.ink3 }}>
                  {h.author} · {h.ts.slice(0, 19).replace("T", " ")} ·{" "}
                  <code>{h.sha.slice(0, 7)}</code>
                </div>
              </div>
              <Button size="small" onClick={() => setPreviewRef(h.sha)}>
                Preview
              </Button>
              <Popconfirm
                title="Restore this version?"
                description="Its content becomes a new commit on top — history is preserved."
                onConfirm={() => onRestore(h.sha)}
                okText="Restore"
              >
                <Button size="small" loading={restore.isPending}>
                  Restore
                </Button>
              </Popconfirm>
            </div>
          ))}
        </Space>
      </div>

      {diff.isError && (
        <Alert type="error" showIcon message="Diff failed" description={(diff.error as Error)?.message} />
      )}
      {diff.data && <DiffViewer diff={diff.data.diff} />}

      <Modal
        open={!!previewRef}
        title={preview.data ? `${preview.data.title} @ ${previewRef?.slice(0, 12)}` : "Preview"}
        footer={null}
        width={720}
        onCancel={() => setPreviewRef(null)}
      >
        {preview.isFetching ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Spin />
          </div>
        ) : (
          <pre
            style={{
              maxHeight: 460,
              overflow: "auto",
              fontSize: 12,
              whiteSpace: "pre-wrap",
              background: tokens.color.surface,
              padding: 12,
              borderRadius: 8,
            }}
          >
            {preview.data?.content}
          </pre>
        )}
      </Modal>
    </Space>
  );
}

export default VersionManager;
