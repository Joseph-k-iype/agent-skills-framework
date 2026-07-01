import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "lid-1" }),
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children?: React.ReactNode }) => <a>{children}</a>,
}));

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

vi.mock("../../api/publicMarketplaceApi", () => ({
  usePublicListing: vi.fn(),
  useListingHistory: vi.fn(),
}));

vi.mock("@/stores/authStore", () => ({
  useAuthStore: (sel: (s: unknown) => unknown) =>
    sel({ user: { id: "u1", username: "dev", permissions: ["skill:create"] } }),
}));

import { useListingHistory, usePublicListing } from "../../api/publicMarketplaceApi";
import MarketplaceDetailPage from "../MarketplaceDetailPage";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>{ui}</AntApp>
    </QueryClientProvider>,
  );
}

describe("MarketplaceDetailPage", () => {
  it("renders the stat strip, chart, and a Clone to workspace button", () => {
    vi.mocked(usePublicListing).mockReturnValue({
      data: {
        id: "lid-1",
        title: "My Skill",
        summary: "does things",
        type: "skill",
        featured: false,
        version: "1.0.0",
        tags: [],
        downloads: 42,
        clones: 5,
        content: "# Readme",
        versions: [{ version: 2, sha: "abcdef0", changelog: null, created_at: "2026-06-01T00:00:00Z" }],
        latest_version: 2,
        created_at: "2026-01-01T00:00:00Z",
      },
      isLoading: false,
    } as unknown as ReturnType<typeof usePublicListing>);
    vi.mocked(useListingHistory).mockReturnValue({
      data: [{ date: "2026-06-01", cumulative: 5 }],
      isLoading: false,
    } as unknown as ReturnType<typeof useListingHistory>);

    wrap(<MarketplaceDetailPage />);

    // Stat strip values
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    // Chart present
    expect(screen.getByTestId("area")).toBeInTheDocument();
    // Clone button (replaces the coming-soon note)
    expect(screen.getByRole("button", { name: /clone to workspace/i })).toBeInTheDocument();
    expect(screen.queryByText(/coming in a later phase/i)).not.toBeInTheDocument();
  });
});
