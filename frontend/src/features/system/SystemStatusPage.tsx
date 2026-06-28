import { useQuery } from "@tanstack/react-query";
import { Badge, Card, Space, Typography } from "antd";
import { http, unwrap } from "@/shared/api/client";
import { tokens } from "@/app/theme/tokens";

interface Readiness {
  ready: boolean;
  postgres: boolean;
  falkordb: boolean;
}

function useReadiness() {
  return useQuery({
    queryKey: ["readyz"],
    queryFn: () => unwrap<Readiness>(http.get("/readyz")),
    refetchInterval: 5000,
  });
}

function StatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <Space size="middle">
      <Badge status={ok ? "success" : "error"} />
      <Typography.Text style={{ width: 120, display: "inline-block" }}>{label}</Typography.Text>
      <Typography.Text type={ok ? "success" : "danger"}>{ok ? "connected" : "down"}</Typography.Text>
    </Space>
  );
}

export default function SystemStatusPage() {
  const { data, isLoading } = useReadiness();
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <Card style={{ width: 440, maxWidth: "100%" }} loading={isLoading}>
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <div>
            <div style={{ fontSize: 12, letterSpacing: "0.18em", color: tokens.color.ink3 }}>
              EAKSO
            </div>
            <Typography.Title level={3} style={{ margin: "4px 0 0" }}>
              System status
            </Typography.Title>
            <Typography.Text type="secondary">
              Enterprise AI Knowledge &amp; Skills Operating System
            </Typography.Text>
          </div>
          <Space direction="vertical" size="middle">
            <StatusRow label="API" ok />
            <StatusRow label="PostgreSQL" ok={!!data?.postgres} />
            <StatusRow label="FalkorDB" ok={!!data?.falkordb} />
          </Space>
        </Space>
      </Card>
    </div>
  );
}
