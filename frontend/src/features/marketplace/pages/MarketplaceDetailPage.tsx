import { ArrowLeftOutlined, CopyOutlined } from "@ant-design/icons";
import { Button, Grid, Select, Skeleton, Tag, Tooltip, Typography, message } from "antd";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { MarkdownPreview } from "@/features/concepts/components/MarkdownPreview";
import { useAuthStore } from "@/stores/authStore";
import { usePublicListing, type VersionRef } from "../api/publicMarketplaceApi";
import { accentFor } from "../theme";

function formatDate(iso?: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function shortSha(sha?: string | null): string {
  return sha ? sha.slice(0, 7) : "—";
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const copy = () => {
    navigator.clipboard?.writeText(text).then(
      () => message.success(label ?? "Copied"),
      () => message.error("Couldn't copy"),
    );
  };
  return <Button type="text" size="small" icon={<CopyOutlined />} onClick={copy} />;
}

export default function MarketplaceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const screens = Grid.useBreakpoint();
  const isWide = screens.lg ?? true;
  const listing = usePublicListing(id);
  const d = listing.data;
  const accent = accentFor(d?.type);

  const [selectedVersion, setSelectedVersion] = useState<number | undefined>(undefined);

  const versions: VersionRef[] = useMemo(() => d?.versions ?? [], [d]);

  const selected: VersionRef | undefined = useMemo(() => {
    if (versions.length === 0) return undefined;
    if (selectedVersion === undefined) return versions[0];
    return versions.find((v) => v.version === selectedVersion) ?? versions[0];
  }, [versions, selectedVersion]);

  const selectedSha = selected?.sha ?? d?.latest_sha ?? "";

  const snippet = selectedSha
    ? `curl ${window.location.origin}/api/v1/public/skills/${selectedSha}`
    : "";

  const useSkill = () => {
    if (!user) {
      navigate(`/login?next=/marketplace/${id}`);
      return;
    }
    navigator.clipboard?.writeText(snippet).then(
      () => message.success("Copied API call"),
      () => message.error("Couldn't copy"),
    );
  };

  if (listing.isLoading) {
    return (
      <div style={{ paddingBottom: 60, maxWidth: 1040 }}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    );
  }

  if (!d) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center" }}>
        <Typography.Text style={{ color: tokens.color.ink3 }}>
          This skill couldn&apos;t be found.
        </Typography.Text>
        <div style={{ marginTop: 12 }}>
          <Link to="/marketplace" style={{ color: tokens.color.accent, fontSize: 13 }}>
            ← Back to marketplace
          </Link>
        </div>
      </div>
    );
  }

  const category = d.category ?? d.type ?? "skill";

  return (
    <div style={{ paddingBottom: 60 }}>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/marketplace")}
        style={{ marginBottom: 12, paddingLeft: 0 }}
      >
        Marketplace
      </Button>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
          {d.featured && (
            <span
              style={{
                font: "600 9px " + tokens.font.sans,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: tokens.color.accent,
                background: "rgba(232,33,39,0.08)",
                padding: "4px 7px",
                borderRadius: 999,
              }}
            >
              ★ Featured
            </span>
          )}
          <span
            style={{
              font: "600 10px " + tokens.font.sans,
              color: tokens.color.ink2,
              background: tokens.color.canvas,
              border: `1px solid ${tokens.color.line}`,
              padding: "4px 7px",
              borderRadius: 999,
              textTransform: "capitalize",
            }}
          >
            {category}
          </span>
        </div>

        <Typography.Title
          level={2}
          style={{ margin: 0, fontFamily: 'ui-serif, Georgia, "Times New Roman", serif' }}
        >
          {d.title}
        </Typography.Title>

        {d.summary && (
          <Typography.Paragraph style={{ fontSize: 15, color: tokens.color.ink2, marginTop: 8, marginBottom: 12 }}>
            {d.summary}
          </Typography.Paragraph>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <span style={{ font: "500 12px " + tokens.font.sans, color: tokens.color.ink2 }}>
            @{d.author_id ? d.author_id.slice(0, 8) : "anonymous"}
          </span>
          <span style={{ font: "600 12px " + tokens.font.sans, color: tokens.color.ink3 }}>★ —</span>
          <span style={{ font: "400 12px " + tokens.font.sans, color: tokens.color.ink3 }}>
            {d.downloads} uses
          </span>

          {versions.length > 0 ? (
            <Select
              size="small"
              value={selected?.version}
              onChange={(v) => setSelectedVersion(v)}
              style={{ minWidth: 160 }}
              options={versions.map((v) => ({
                value: v.version,
                label: `v${v.version} · ${shortSha(v.sha)}`,
              }))}
            />
          ) : (
            <Tag bordered={false}>v{d.latest_version ?? d.version}</Tag>
          )}

          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              font: "500 11px " + tokens.font.mono,
              color: tokens.color.ink2,
              background: tokens.color.canvas,
              border: `1px solid ${tokens.color.line}`,
              padding: "3px 4px 3px 9px",
              borderRadius: 999,
            }}
          >
            sha256:{selectedSha || "—"}
            {selectedSha && <CopyButton text={`sha256:${selectedSha}`} label="Copied SHA" />}
          </span>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isWide ? "1.5fr 1fr" : "1fr",
          gap: 28,
        }}
      >
        {/* Main: rendered README */}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              background: tokens.color.surface,
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              padding: 24,
            }}
          >
            <MarkdownPreview source={d.content} />
          </div>
        </div>

        {/* Right: action panel */}
        <div>
          <div
            style={{
              border: `1px solid ${tokens.color.line}`,
              borderRadius: 16,
              padding: 20,
              position: isWide ? "sticky" : "static",
              top: 16,
              background: tokens.color.surface,
            }}
          >
            <Tooltip title={user ? "Copies the API call" : "Sign in to use this skill"}>
              <Button
                block
                onClick={useSkill}
                style={{
                  background: tokens.color.ink,
                  color: tokens.color.surface,
                  border: "none",
                  height: 40,
                  fontWeight: 600,
                }}
              >
                Use skill
              </Button>
            </Tooltip>

            <div style={{ height: 20 }} />

            <Typography.Text strong style={{ display: "block", marginBottom: 8, fontSize: 13 }}>
              API snippet
            </Typography.Text>
            <div
              style={{
                borderRadius: 10,
                border: `1px solid ${tokens.color.line}`,
                background: tokens.color.canvas,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "6px 10px",
                  borderBottom: `1px solid ${tokens.color.line}`,
                }}
              >
                <span style={{ font: "500 10px " + tokens.font.mono, color: tokens.color.ink3 }}>
                  shell
                </span>
                {snippet && <CopyButton text={snippet} />}
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: 12,
                  fontSize: 11.5,
                  lineHeight: 1.6,
                  fontFamily: tokens.font.mono,
                  color: tokens.color.ink,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {snippet || "No published version yet."}
              </pre>
            </div>
            <Typography.Paragraph
              type="secondary"
              style={{ fontSize: 11.5, marginTop: 8, marginBottom: 0 }}
            >
              Clone to workspace &amp; SDK snippets — coming in a later phase.
            </Typography.Paragraph>

            <div style={{ height: 24 }} />

            <Typography.Text strong style={{ display: "block", marginBottom: 10, fontSize: 13 }}>
              Versions &amp; changelog
            </Typography.Text>
            {versions.length === 0 ? (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                No version history yet.
              </Typography.Text>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {versions.map((v) => (
                  <div
                    key={v.version}
                    style={{
                      paddingBottom: 10,
                      borderBottom: `1px solid ${tokens.color.line}`,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ font: "600 12px " + tokens.font.sans, color: tokens.color.ink }}>
                        v{v.version}
                      </span>
                      <span style={{ font: "500 11px " + tokens.font.mono, color: accent }}>
                        {shortSha(v.sha)}
                      </span>
                      <span style={{ font: "400 11px " + tokens.font.sans, color: tokens.color.ink3 }}>
                        {formatDate(v.created_at)}
                      </span>
                    </div>
                    {v.changelog && (
                      <div
                        style={{
                          font: "400 12px/1.5 " + tokens.font.sans,
                          color: tokens.color.ink2,
                          marginTop: 4,
                        }}
                      >
                        {v.changelog}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
