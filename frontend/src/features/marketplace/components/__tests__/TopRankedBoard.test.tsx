import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  Link: ({ children, to }: { children?: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("../../api/publicMarketplaceApi", () => ({ useTopRanked: vi.fn() }));
// NumberTicker animates via rAF; render its value directly for a stable assert.
vi.mock("@/features/shared/fancy/NumberTicker", () => ({
  NumberTicker: ({ value }: { value: number }) => <span>{value}</span>,
}));
vi.mock("@/features/shared/fancy/Reveal", () => ({
  Reveal: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/shared/fancy/Shimmer", () => ({
  Shimmer: () => <div data-testid="shimmer" />,
}));

import { useTopRanked } from "../../api/publicMarketplaceApi";
import { TopRankedBoard } from "../TopRankedBoard";

const listing = (id: string, title: string, downloads: number) => ({
  id,
  title,
  featured: false,
  version: "1",
  tags: [],
  downloads,
  category: "extraction",
  type: "skill",
});

describe("TopRankedBoard", () => {
  it("renders ranked rows 01/02/03 with titles and use counts", () => {
    vi.mocked(useTopRanked).mockReturnValue({
      data: [listing("a", "Alpha", 300), listing("b", "Beta", 150), listing("c", "Gamma", 30)],
      isLoading: false,
    } as unknown as ReturnType<typeof useTopRanked>);

    render(<TopRankedBoard />);
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("300")).toBeInTheDocument();
    // Title links to the detail route.
    expect(screen.getByText("Alpha").closest("a")).toHaveAttribute("href", "/marketplace/a");
  });

  it("renders nothing when the leaderboard is empty", () => {
    vi.mocked(useTopRanked).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useTopRanked>);
    const { container } = render(<TopRankedBoard />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows shimmer rows while loading", () => {
    vi.mocked(useTopRanked).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof useTopRanked>);
    render(<TopRankedBoard />);
    expect(screen.getAllByTestId("shimmer").length).toBe(8);
  });
});
