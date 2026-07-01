import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// recharts' ResponsiveContainer needs layout dims jsdom doesn't provide; stub the
// primitives to plain divs so the component renders deterministically in tests.
vi.mock("recharts", () => {
  const Pass = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  return {
    ResponsiveContainer: Pass,
    AreaChart: Pass,
    Area: () => <div data-testid="area" />,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
  };
});

import { DownloadHistoryChart } from "../DownloadHistoryChart";

describe("DownloadHistoryChart", () => {
  it("renders an area series from mocked points", () => {
    render(
      <DownloadHistoryChart
        data={[
          { date: "2026-06-01", cumulative: 3 },
          { date: "2026-06-10", cumulative: 8 },
        ]}
      />,
    );
    expect(screen.getByTestId("area")).toBeInTheDocument();
  });

  it("shows an empty state when the series is empty", () => {
    render(<DownloadHistoryChart data={[]} />);
    expect(screen.getByText(/no usage yet/i)).toBeInTheDocument();
    expect(screen.queryByTestId("area")).not.toBeInTheDocument();
  });
});
