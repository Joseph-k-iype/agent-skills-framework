import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Mock the API module before importing the component
vi.mock("../../api/apiKeysApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/apiKeysApi")>();
  return {
    ...actual,
    useKeyUsage: vi.fn(),
  };
});

import { useKeyUsage } from "../../api/apiKeysApi";
import { KeyUsagePanel } from "../KeyUsagePanel";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>{ui}</AntApp>
    </QueryClientProvider>,
  );
}

describe("KeyUsagePanel", () => {
  it("renders total count and by_kind breakdown from a mocked usage response", () => {
    vi.mocked(useKeyUsage).mockReturnValue({
      data: {
        total: 42,
        last_used_at: "2026-06-15T10:30:00Z",
        by_kind: { concept_eval: 30, sdk_call: 12 },
        by_skill: [{ listing_id: "s1", title: "My Skill", count: 10 }],
        recent: [{ kind: "concept_eval", listing_id: null, created_at: "2026-06-15T10:30:00Z" }],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useKeyUsage>);

    wrap(<KeyUsagePanel keyId="key-123" />);

    // Total usage visible
    expect(screen.getAllByText("42").length).toBeGreaterThan(0);
    // By-kind breakdown
    expect(screen.getAllByText("concept_eval").length).toBeGreaterThan(0);
    expect(screen.getAllByText("30").length).toBeGreaterThan(0);
    expect(screen.getAllByText("sdk_call").length).toBeGreaterThan(0);
    expect(screen.getAllByText("12").length).toBeGreaterThan(0);
    // Last used date
    expect(screen.getAllByText(/2026-06-15/).length).toBeGreaterThan(0);
  });

  it("shows empty state when total is 0", () => {
    vi.mocked(useKeyUsage).mockReturnValue({
      data: {
        total: 0,
        last_used_at: null,
        by_kind: {},
        by_skill: [],
        recent: [],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useKeyUsage>);

    wrap(<KeyUsagePanel keyId="key-456" />);

    expect(screen.getByText(/no usage yet/i)).toBeInTheDocument();
    // Should not show a count of "0" as a data value
    expect(screen.queryByRole("cell", { name: "0" })).not.toBeInTheDocument();
  });

  it("shows loading state while fetching", () => {
    vi.mocked(useKeyUsage).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useKeyUsage>);

    wrap(<KeyUsagePanel keyId="key-789" />);
    // Component renders without crashing; no usage data shown
    expect(screen.queryByText(/no usage yet/i)).not.toBeInTheDocument();
  });
});
