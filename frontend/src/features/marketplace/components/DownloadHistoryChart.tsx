import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { tokens } from "@/app/theme/tokens";
import type { HistoryPoint } from "../api/publicMarketplaceApi";

interface DownloadHistoryChartProps {
  data: HistoryPoint[];
  height?: number;
}

/** Cumulative uses-over-time area chart (Swiss-minimal). Empty-state on []. */
export function DownloadHistoryChart({ data, height = 220 }: DownloadHistoryChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          border: `1px dashed ${tokens.color.line}`,
          borderRadius: tokens.radius,
          color: tokens.color.ink3,
          font: "400 13px " + tokens.font.sans,
        }}
      >
        No usage yet.
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="usesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={tokens.color.accent} stopOpacity={0.18} />
              <stop offset="100%" stopColor={tokens.color.accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={tokens.color.line} vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: tokens.color.ink3, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: tokens.color.line }}
            minTickGap={24}
          />
          <YAxis
            tick={{ fill: tokens.color.ink3, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            width={36}
          />
          <Tooltip
            contentStyle={{
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              fontFamily: tokens.font.mono,
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke={tokens.color.accent}
            strokeWidth={2}
            fill="url(#usesFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
