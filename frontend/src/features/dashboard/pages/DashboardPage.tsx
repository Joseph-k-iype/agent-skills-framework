import { AppstoreOutlined, DeploymentUnitOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { Card, Col, Row, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { useAuthStore } from "@/stores/authStore";

const QUICK = [
  { to: "/workspace", icon: FolderOpenOutlined, title: "Workspace", body: "Organize knowledge packages, folders and assets." },
  { to: "/knowledge", icon: DeploymentUnitOutlined, title: "Knowledge Graph", body: "Import OKF and search across the graph." },
  { to: "/skills", icon: AppstoreOutlined, title: "Skills", body: "Author, version and publish agent skills." },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title={`Welcome back, ${user?.full_name ?? user?.username ?? ""}`}
        description="Your enterprise knowledge and skills, at a glance."
      />
      <Row gutter={[16, 16]}>
        {QUICK.map((q) => (
          <Col xs={24} md={8} key={q.to}>
            <Card hoverable onClick={() => navigate(q.to)} style={{ height: "100%" }}>
              <q.icon style={{ fontSize: 22, color: tokens.color.accent }} />
              <Typography.Title level={4} style={{ margin: "14px 0 4px" }}>
                {q.title}
              </Typography.Title>
              <Typography.Text type="secondary">{q.body}</Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
