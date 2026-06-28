import { Typography } from "antd";
import type { ReactNode } from "react";
import { tokens } from "@/app/theme/tokens";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-between",
        marginBottom: 28,
        gap: 16,
      }}
    >
      <div>
        {eyebrow && (
          <div style={{ fontSize: 12, letterSpacing: "0.16em", color: tokens.color.ink3, textTransform: "uppercase" }}>
            {eyebrow}
          </div>
        )}
        <Typography.Title level={2} style={{ margin: "6px 0 0", fontSize: 28 }}>
          {title}
        </Typography.Title>
        {description && (
          <Typography.Text type="secondary" style={{ fontSize: 15 }}>
            {description}
          </Typography.Text>
        )}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
}
