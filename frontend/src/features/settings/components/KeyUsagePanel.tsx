import { Skeleton, Table, Typography } from "antd";
import { tokens } from "@/app/theme/tokens";
import { useKeyUsage, type KeyUsageEvent, type KeyUsageSkill } from "../api/apiKeysApi";

const { Text } = Typography;

const mono: React.CSSProperties = { fontFamily: tokens.font.mono };

const panelStyle: React.CSSProperties = {
  border: `1px solid ${tokens.color.line}`,
  borderRadius: 4,
  padding: "12px 16px",
  background: tokens.color.surface,
  marginTop: 8,
};

interface Props {
  keyId: string;
}

export function KeyUsagePanel({ keyId }: Props) {
  const { data, isLoading } = useKeyUsage(keyId);

  if (isLoading) {
    return (
      <div style={panelStyle}>
        <Skeleton active paragraph={{ rows: 2 }} title={false} />
      </div>
    );
  }

  if (!data || data.total === 0) {
    return (
      <div style={panelStyle}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          No usage yet
        </Text>
      </div>
    );
  }

  const byKindRows = Object.entries(data.by_kind).map(([kind, count]) => ({ kind, count }));

  return (
    <div style={panelStyle}>
      {/* Summary row */}
      <div style={{ display: "flex", gap: 24, marginBottom: 12, alignItems: "baseline" }}>
        <span>
          <Text type="secondary" style={{ fontSize: 11, marginRight: 6 }}>
            Total calls
          </Text>
          <Text strong style={{ ...mono, fontSize: 15 }}>
            {data.total}
          </Text>
        </span>
        {data.last_used_at && (
          <span>
            <Text type="secondary" style={{ fontSize: 11, marginRight: 6 }}>
              Last used
            </Text>
            <Text style={{ ...mono, fontSize: 12 }}>
              {data.last_used_at.slice(0, 16).replace("T", " ")}
            </Text>
          </span>
        )}
      </div>

      {/* By-kind breakdown */}
      {byKindRows.length > 0 && (
        <Table<{ kind: string; count: number }>
          dataSource={byKindRows}
          rowKey="kind"
          size="small"
          pagination={false}
          showHeader={false}
          style={{ marginBottom: 8 }}
          columns={[
            {
              dataIndex: "kind",
              key: "kind",
              render: (k: string) => (
                <Text style={{ ...mono, fontSize: 12 }}>{k}</Text>
              ),
            },
            {
              dataIndex: "count",
              key: "count",
              align: "right" as const,
              width: 64,
              render: (c: number) => (
                <Text strong style={{ ...mono, fontSize: 12 }}>
                  {c}
                </Text>
              ),
            },
          ]}
        />
      )}

      {/* Recent events */}
      {data.recent.length > 0 && (
        <>
          <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 4 }}>
            Recent
          </Text>
          {data.recent.slice(0, 5).map((ev: KeyUsageEvent, i: number) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "2px 0",
                borderTop: i === 0 ? `1px solid ${tokens.color.line}` : undefined,
              }}
            >
              <Text style={{ ...mono, fontSize: 11, color: tokens.color.ink2 }}>{ev.kind}</Text>
              <Text style={{ ...mono, fontSize: 11, color: tokens.color.ink3 }}>
                {ev.created_at.slice(0, 16).replace("T", " ")}
              </Text>
            </div>
          ))}
        </>
      )}

      {/* By-skill breakdown */}
      {data.by_skill.length > 0 && (
        <Table<KeyUsageSkill>
          dataSource={data.by_skill}
          rowKey="listing_id"
          size="small"
          pagination={false}
          style={{ marginTop: 8 }}
          columns={[
            { title: "Skill", dataIndex: "title", key: "title" },
            {
              title: "Calls",
              dataIndex: "count",
              key: "count",
              align: "right" as const,
              width: 64,
              render: (c: number) => (
                <Text style={{ ...mono, fontSize: 12 }}>{c}</Text>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
