import { useState } from "react";
import { Button, Select, Typography } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { MarkdownPreview } from "@/features/concepts/components/MarkdownPreview";
import { tokens } from "@/app/theme/tokens";
import { QUICKSTART_MD, API_DOWNLOAD_URL } from "../docs";
import { useSkillListings } from "../api/sdkApi";

const { Title, Text } = Typography;

function buildSnippet(skillId: string): string {
  return `import os
from eakso import Client, Skill

client = Client(api_key=os.environ["EAKSO_API_KEY"])

skill = Skill(client=client, skill_id="${skillId}")
result = skill.apply({"input": "Hello, EAKSO!"})
print(result)`;
}

export default function SdkDocsPage() {
  const { data: listings = [], isLoading } = useSkillListings();
  const [selectedSkillId, setSelectedSkillId] = useState<string>("<skill-id>");

  const snippet = buildSnippet(selectedSkillId);

  const skillOptions = listings.map((l) => ({ value: l.id, label: l.title }));

  return (
    <div
      style={{
        maxWidth: 860,
        margin: "0 auto",
        padding: "32px 24px",
        fontFamily: tokens.font.sans,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
          paddingBottom: 16,
          borderBottom: `1px solid ${tokens.color.line}`,
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0, color: tokens.color.ink }}>
            SDK Docs
          </Title>
          <Text style={{ color: tokens.color.ink2, fontSize: 13 }}>
            Install · Quickstart · API Reference
          </Text>
        </div>
        <Button
          href={API_DOWNLOAD_URL}
          icon={<DownloadOutlined />}
          data-testid="download-sdk-btn"
          style={{
            borderColor: tokens.color.lineStrong,
            borderRadius: tokens.radius / 2,
            fontFamily: tokens.font.sans,
          }}
        >
          Download SDK
        </Button>
      </div>

      {/* Quickstart */}
      <section style={{ marginBottom: 40 }}>
        <MarkdownPreview source={QUICKSTART_MD} />
      </section>

      {/* Prefilled snippet */}
      <section
        style={{
          border: `1px solid ${tokens.color.line}`,
          borderRadius: tokens.radius / 2,
          padding: 20,
          backgroundColor: tokens.color.surface,
          marginBottom: 40,
        }}
      >
        <Title level={5} style={{ margin: "0 0 12px", color: tokens.color.ink }}>
          Try it — prefilled snippet
        </Title>

        <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 12 }}>
          <Text style={{ color: tokens.color.ink2, fontSize: 13, flexShrink: 0 }}>
            Select skill:
          </Text>
          <Select
            style={{ minWidth: 260 }}
            loading={isLoading}
            placeholder="Choose a marketplace skill"
            options={skillOptions}
            value={selectedSkillId === "<skill-id>" ? undefined : selectedSkillId}
            onChange={(val: string) => setSelectedSkillId(val)}
            data-testid="skill-select"
            allowClear
            onClear={() => setSelectedSkillId("<skill-id>")}
          />
        </div>

        <pre
          data-testid="sdk-snippet"
          style={{
            fontFamily: tokens.font.mono,
            fontSize: 13,
            lineHeight: 1.6,
            backgroundColor: tokens.color.canvas,
            border: `1px solid ${tokens.color.line}`,
            borderRadius: tokens.radius / 2,
            padding: "14px 16px",
            margin: 0,
            overflowX: "auto",
            color: tokens.color.ink,
            whiteSpace: "pre",
          }}
        >
          {snippet}
        </pre>
      </section>
    </div>
  );
}
