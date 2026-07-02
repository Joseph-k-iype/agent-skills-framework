import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  Link: ({ children }: { children?: React.ReactNode }) => <a>{children}</a>,
}));
vi.mock("../../api/publicMarketplaceApi", () => ({ useInfiniteMarketplace: vi.fn() }));
// Control the sentinel: default to "in view" so an available next page fetches.
vi.mock("@/features/shared/fancy/useInView", () => ({ useInView: vi.fn() }));
vi.mock("@/features/shared/fancy/Reveal", () => ({
  Reveal: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/shared/fancy/Spotlight", () => ({
  Spotlight: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/shared/fancy/Shimmer", () => ({
  Shimmer: () => <div data-testid="shimmer" />,
}));

import { useInfiniteMarketplace } from "../../api/publicMarketplaceApi";
import { useInView } from "@/features/shared/fancy/useInView";
import { InfiniteSkillGrid } from "../InfiniteSkillGrid";

const card = (id: string) => ({
  id,
  title: `Card ${id}`,
  summary: "s",
  type: "skill",
  featured: false,
  version: "1",
  tags: [],
  downloads: 0,
});

function mockGrid(over: Record<string, unknown>) {
  vi.mocked(useInfiniteMarketplace).mockReturnValue({
    data: { pages: [[card("1"), card("2")], [card("3")]], pageParams: [0, 24] },
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    ...over,
  } as unknown as ReturnType<typeof useInfiniteMarketplace>);
}

describe("InfiniteSkillGrid", () => {
  it("flattens all pages into cards", () => {
    vi.mocked(useInView).mockReturnValue([{ current: null }, false]);
    mockGrid({});
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(screen.getByText("Card 1")).toBeInTheDocument();
    expect(screen.getByText("Card 2")).toBeInTheDocument();
    expect(screen.getByText("Card 3")).toBeInTheDocument();
  });

  it("calls fetchNextPage when the sentinel is in view and there is a next page", () => {
    const fetchNextPage = vi.fn();
    vi.mocked(useInView).mockReturnValue([{ current: null }, true]);
    mockGrid({ hasNextPage: true, fetchNextPage });
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it("does not fetch and shows the end marker when there is no next page", () => {
    const fetchNextPage = vi.fn();
    vi.mocked(useInView).mockReturnValue([{ current: null }, true]);
    mockGrid({ hasNextPage: false, fetchNextPage });
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(fetchNextPage).not.toHaveBeenCalled();
    expect(screen.getByText(/end of results/i)).toBeInTheDocument();
  });

  it("shows a shimmer row while fetching the next page", () => {
    vi.mocked(useInView).mockReturnValue([{ current: null }, false]);
    mockGrid({ hasNextPage: true, isFetchingNextPage: true });
    render(<InfiniteSkillGrid params={{ sort: "uses" }} masonryClass="m" />);
    expect(screen.getAllByTestId("shimmer").length).toBeGreaterThan(0);
  });
});
