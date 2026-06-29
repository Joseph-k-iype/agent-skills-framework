import { DeploymentUnitOutlined, FileTextOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { Card, Col, Row, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { useAuthStore } from "@/stores/authStore";

const QUICK = [
  { to: "/workspace", icon: FolderOpenOutlined, title: "Workspace", body: "Folders and markdown concepts — skills, agents, prompts, docs." },
  { to: "/workspace", icon: FileTextOutlined, title: "Author a concept", body: "Write a skill with a body, mermaid diagrams and a free-text runtime." },
  { to: "/knowledge", icon: DeploymentUnitOutlined, title: "Knowledge Graph", body: "Search concepts and explore how they link together." },
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
