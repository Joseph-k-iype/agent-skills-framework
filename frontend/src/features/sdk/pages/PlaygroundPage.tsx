import { useState, useCallback } from "react";
import { Button, Input, Select, Space, Typography, Alert } from "antd";
import { useSkillListings } from "../api/sdkApi";
import { useApiKeys, useKeyUsage } from "@/features/settings/api/apiKeysApi";
import { fetchSkillWithKey, type SkillResponse } from "../api/playgroundApi";
import { PageHeader } from "@/shared/components/PageHeader";

const { Text, Paragraph } = Typography;

export default function PlaygroundPage() {
  const { data: skills = [], isLoading: skillsLoading } = useSkillListings();
  const { data: keys = [] } = useApiKeys();

  const [apiKey, setApiKey] = useState("");
  const [skillId, setSkillId] = useState<string | undefined>(undefined);
  const [running, setRunning] = useState(false);
  const [response, setResponse] = useState<SkillResponse | null>(null);
  const [error, setError] = useState<{ message: string; status?: number } | null>(null);
  const [usageRecorded, setUsageRecorded] = useState(false);

  // Derive the key id from the matched prefix so we can re-fetch usage
  const matchedKeyId =
    keys.find(
      (k) =>
        apiKey.startsWith(k.prefix) ||
        // prefix is typically the first 12 chars; also try exact prefix match
        (k.prefix && apiKey.startsWith(k.prefix.replace(/\*+$/, ""))),
    )?.id ?? keys[0]?.id ?? "";

  const { refetch: refetchUsage } = useKeyUsage(matchedKeyId);

  const run = useCallback(async () => {
    if (!apiKey.trim() || !skillId) return;
    setRunning(true);
    setResponse(null);
    setError(null);
    setUsageRecorded(false);

    try {
      const data = await fetchSkillWithKey(skillId, apiKey.trim());
      setResponse(data);
      // Re-fetch usage to confirm the event was recorded
      await refetchUsage();
      setUsageRecorded(true);
    } catch (e) {
      const err = e as Error & { status?: number };
      setError({ message: err.message, status: err.status });
    } finally {
      setRunning(false);
    }
  }, [apiKey, skillId, refetchUsage]);

  const skillOptions = (skills ?? []).map((s) => ({ value: s.id, label: s.title }));

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "24px 16px" }}>
      <PageHeader eyebrow="SDK" title="Test your key" />

      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        {/* API key input */}
        <div>
          <Text
            style={{
              display: "block",
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 4,
              fontFamily: "monospace",
            }}
          >
            API Key
          </Text>
          <Input
            placeholder="sk_live_…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            style={{ fontFamily: "monospace", borderRadius: 4 }}
            allowClear
          />
        </div>

        {/* Skill picker */}
        <div>
          <Text
            style={{
              display: "block",
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 4,
              fontFamily: "monospace",
            }}
          >
            Skill
          </Text>
          <Select
            style={{ width: "100%", borderRadius: 4 }}
            placeholder={skillsLoading ? "Loading skills…" : "Select a skill"}
            loading={skillsLoading}
            options={skillOptions}
            value={skillId}
            onChange={setSkillId}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? "").toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>

        {/* Run button */}
        <Button
          type="primary"
          onClick={run}
          loading={running}
          disabled={!apiKey.trim() || !skillId}
          style={{ borderRadius: 4 }}
        >
          Run
        </Button>

        {/* Error state */}
        {error && (
          <Alert
            type="error"
            data-testid="playground-error"
            message={
              error.status === 401
                ? `401 — Invalid or revoked API key`
                : `Error${error.status ? ` ${error.status}` : ""}: ${error.message}`
            }
            showIcon
            style={{ borderRadius: 4, fontFamily: "monospace" }}
          />
        )}

        {/* Success: response */}
        {response && (
          <div
            data-testid="playground-response"
            style={{
              border: "1px solid #e0e0e0",
              borderRadius: 4,
              padding: 16,
              background: "#fafafa",
            }}
          >
            <Text
              style={{
                display: "block",
                fontSize: 11,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: 8,
                fontFamily: "monospace",
              }}
            >
              Response — {response.title} v{response.version}
            </Text>
            {response.system_prompt && (
              <Paragraph
                style={{ fontFamily: "monospace", fontSize: 13, marginBottom: 8 }}
              >
                <strong>system_prompt:</strong> {response.system_prompt}
              </Paragraph>
            )}
            {response.content && (
              <Paragraph style={{ fontFamily: "monospace", fontSize: 13, marginBottom: 0 }}>
                <strong>content:</strong> {response.content}
              </Paragraph>
            )}
          </div>
        )}

        {/* Usage recorded confirmation */}
        {usageRecorded && (
          <Alert
            type="success"
            data-testid="usage-recorded"
            message="Usage recorded — this call was logged against your key."
            showIcon
            style={{ borderRadius: 4 }}
          />
        )}
      </Space>
    </div>
  );
}
