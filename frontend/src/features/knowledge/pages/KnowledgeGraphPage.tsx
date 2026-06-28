import { ImportOutlined, SearchOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Col, Input, List, Modal, Row, Tag, Typography } from "antd";
import { useState } from "react";
import { PageHeader } from "@/shared/components/PageHeader";
import { tokens } from "@/app/theme/tokens";
import { GraphRelationshipView } from "../components/GraphRelationshipView";
import { useImportOkf, useNeighborhood, useSearch } from "../api/knowledgeApi";

export default function KnowledgeGraphPage() {
  const { message } = AntApp.useApp();
  const [term, setTerm] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [source, setSource] = useState("");

  const search = useSearch(submitted, !!submitted);
  const neighborhood = useNeighborhood(selected);
  const importOkf = useImportOkf();

  async function runImport() {
    if (!source.trim()) return;
    try {
      const res = await importOkf.mutateAsync({ source_repository: source.trim() });
      message.success(
        `Imported ${res.documents} documents, ${res.references} references` +
          (res.orphans.length ? ` (${res.orphans.length} orphan links)` : ""),
      );
      setImportOpen(false);
    } catch (e) {
      message.error((e as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge"
        title="Knowledge Graph"
        description="Import OKF documents and explore them with semantic search."
        actions={
          <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
            Import OKF
          </Button>
        }
      />

      <Input
        size="large"
        allowClear
        prefix={<SearchOutlined style={{ color: tokens.color.ink3 }} />}
        placeholder="Search across enterprise knowledge…"
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        onPressEnter={() => setSubmitted(term)}
        style={{ marginBottom: 20, maxWidth: 720 }}
      />

      <Row gutter={16}>
        <Col xs={24} md={10}>
          <Card title="Results" styles={{ body: { padding: 8 } }}>
            <List
              loading={search.isFetching}
              dataSource={search.data?.results ?? []}
              locale={{ emptyText: submitted ? "No matches" : "Search to see results" }}
              renderItem={(r) => (
                <List.Item
                  onClick={() => setSelected(r.id)}
                  style={{
                    cursor: "pointer",
                    padding: "12px 12px",
                    borderRadius: 8,
                    background: selected === r.id ? "#FCEDED" : undefined,
                  }}
                >
                  <List.Item.Meta
                    title={
                      <span>
                        {r.title} <Tag bordered={false}>{r.type}</Tag>
                      </span>
                    }
                    description={
                      <span style={{ color: tokens.color.ink3, fontSize: 12 }}>
                        {r.relative_path} · {r.provenance.references.length} references
                      </span>
                    }
                  />
                </List.Item>
              )}
            />
            {search.data && (
              <Typography.Text type="secondary" style={{ fontSize: 12, padding: "0 12px" }}>
                {search.data.semantic ? "Semantic embeddings" : "Lexical embeddings (no LLM key)"}
              </Typography.Text>
            )}
          </Card>
        </Col>
        <Col xs={24} md={14}>
          <Card title="Relationships" styles={{ body: { padding: 12 } }}>
            <GraphRelationshipView data={neighborhood.data} />
          </Card>
        </Col>
      </Row>

      <Modal
        title="Import OKF knowledge"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={runImport}
        okText="Import"
        confirmLoading={importOkf.isPending}
      >
        <Typography.Paragraph type="secondary">
          Provide a directory of OKF markdown documents on the server.
        </Typography.Paragraph>
        <Input
          placeholder="/path/to/okf/repo"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          onPressEnter={runImport}
        />
      </Modal>
    </div>
  );
}
