import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  Link: ({ children }: { children?: React.ReactNode }) => <a>{children}</a>,
}));
// Categories + taxonomy hooks used by the hero/filters.
vi.mock("../../api/publicMarketplaceApi", () => ({
  usePublicCategories: vi.fn(() => ({ data: [{ category: "extraction", count: 3 }] })),
}));
vi.mock("@/features/concepts/api/taxonomyApi", () => ({
  useTaxonomyTerms: vi.fn(() => ({ data: { terms: [] } })),
}));
// Board renders a marker only when mounted; grid renders a marker always.
vi.mock("../../components/TopRankedBoard", () => ({
  TopRankedBoard: () => <div data-testid="board" />,
}));
vi.mock("../../components/TrendingMarquee", () => ({
  TrendingMarquee: ({ onPick }: { onPick: (c: string) => void }) => (
    <button type="button" onClick={() => onPick("extraction")}>
      pick-extraction
    </button>
  ),
}));
vi.mock("../../components/InfiniteSkillGrid", () => ({
  InfiniteSkillGrid: () => <div data-testid="grid" />,
}));

import MarketplacePage from "../MarketplacePage";

describe("MarketplacePage", () => {
  it("shows the TopRankedBoard by default and always shows the grid", () => {
    render(<MarketplacePage />);
    expect(screen.getByTestId("board")).toBeInTheDocument();
    expect(screen.getByTestId("grid")).toBeInTheDocument();
  });

  it("hides the TopRankedBoard once a category filter is applied", () => {
    render(<MarketplacePage />);
    // TrendingMarquee's pick sets the category filter → board unmounts.
    fireEvent.click(screen.getByText("pick-extraction"));
    expect(screen.queryByTestId("board")).not.toBeInTheDocument();
    expect(screen.getByTestId("grid")).toBeInTheDocument();
  });

  it("hides the TopRankedBoard once a search query is typed", () => {
    render(<MarketplacePage />);
    fireEvent.change(screen.getByLabelText(/search skills/i), {
      target: { value: "csv" },
    });
    expect(screen.queryByTestId("board")).not.toBeInTheDocument();
  });
});
