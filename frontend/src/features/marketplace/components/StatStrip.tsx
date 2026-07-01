import { tokens } from "@/app/theme/tokens";

function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

interface StatStripProps {
  uses: number;
  clones: number;
  versionCount: number;
  latestVersion?: number | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
      <span
        style={{
          font: "600 20px " + tokens.font.sans,
          color: tokens.color.ink,
          letterSpacing: "-0.01em",
        }}
      >
        {value}
      </span>
      <span
        style={{
          font: "500 11px " + tokens.font.mono,
          color: tokens.color.ink3,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </span>
      {sub && (
        <span style={{ font: "400 11px " + tokens.font.sans, color: tokens.color.ink2 }}>{sub}</span>
      )}
    </div>
  );
}

export function StatStrip({
  uses,
  clones,
  versionCount,
  latestVersion,
  createdAt,
  updatedAt,
}: StatStripProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
        gap: 20,
        padding: "16px 20px",
        border: `1px solid ${tokens.color.line}`,
        borderRadius: tokens.radius,
        background: tokens.color.surface,
      }}
    >
      <Stat label="uses" value={String(uses)} />
      <Stat label="clones" value={String(clones)} />
      <Stat
        label="versions"
        value={String(versionCount)}
        sub={latestVersion != null ? `latest v${latestVersion}` : undefined}
      />
      <Stat label="created" value={fmtDate(createdAt)} sub={`updated ${fmtDate(updatedAt)}`} />
    </div>
  );
}
