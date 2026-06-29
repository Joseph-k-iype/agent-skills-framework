import { SearchOutlined } from "@ant-design/icons";
import { Card, Col, Empty, Input, List, Row, Select, Tag, Typography } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { GraphRelationshipView } from "../components/GraphRelationshipView";
import { useConceptNeighborhood, useWorkspaceSearch } from "../api/knowledgeApi";
import { useWorkspaces } from "@/features/workspace/api/workspaceApi";

export default function KnowledgeGraphPage() {
  const navigate = useNavigate();
  const workspaces = useWorkspaces();
  const [activeWs, setActiveWs] = useState<string | undefined>();
  const wsId = activeWs ?? workspaces.data?.[0]?.id;

  const [term, setTerm] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const search = useWorkspaceSearch(wsId, submitted, !!submitted);
  const neighborhood = useConceptNeighborhood(wsId, selected);

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge"
        title="Knowledge Graph"
        description="Search a workspace's concepts and explore how they link together."
        actions={
          <Select
            placeholder="Select workspace"
            style={{ minWidth: 220 }}
            value={wsId}
            onChange={(v) => {
              setActiveWs(v);
              setSelected(null);
              setSubmitted("");
              setTerm("");
            }}
            options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
          />
        }
      />

      <Input
        size="large"
        allowClear
        prefix={<SearchOutlined style={{ color: tokens.color.ink3 }} />}
        placeholder="Search concepts in this workspace…"
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        onPressEnter={() => setSubmitted(term)}
        style={{ marginBottom: 20, maxWidth: 720 }}
        disabled={!wsId}
      />

      <Row gutter={16}>
        <Col xs={24} md={10}>
          <Card title="Results" styles={{ body: { padding: 8 } }}>
            <List
              loading={search.isFetching}
              dataSource={search.data ?? []}
              locale={{ emptyText: submitted ? "No matches" : "Search to see results" }}
              renderItem={(r) => (
                <List.Item
                  onClick={() => setSelected(r.path)}
                  style={{
                    cursor: "pointer",
                    padding: "12px 12px",
                    borderRadius: 8,
                    background: selected === r.path ? "#FCEDED" : undefined,
                  }}
                  actions={[
                    <a key="open" onClick={() => navigate(`/concepts/${wsId}/${r.path}`)}>
                      open
                    </a>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <span>
                        {r.title} <Tag bordered={false}>{r.type}</Tag>
                        {r.runtime && <Tag bordered={false}>{r.runtime}</Tag>}
                      </span>
                    }
                    description={
                      <span style={{ color: tokens.color.ink3, fontSize: 12 }}>{r.path}</span>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} md={14}>
          <Card title="Relationships" styles={{ body: { padding: 12 } }}>
            {selected ? (
              <GraphRelationshipView data={neighborhood.data} />
            ) : (
              <div style={{ height: 460, display: "grid", placeItems: "center" }}>
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="Select a result to see its linked concepts"
                />
              </div>
            )}
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Edges come from markdown links between concepts — the workspace files are the source.
            </Typography.Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
