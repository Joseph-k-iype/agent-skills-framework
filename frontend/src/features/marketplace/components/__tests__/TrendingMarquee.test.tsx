import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../api/publicMarketplaceApi", () => ({ usePublicCategories: vi.fn() }));
// Marquee duplicates children in real life; render once here for a clean assert.
vi.mock("@/features/shared/fancy/Marquee", () => ({
  Marquee: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));

import { usePublicCategories } from "../../api/publicMarketplaceApi";
import { TrendingMarquee } from "../TrendingMarquee";

describe("TrendingMarquee", () => {
  it("renders a chip per category and fires onPick when clicked", () => {
    vi.mocked(usePublicCategories).mockReturnValue({
      data: [
        { category: "extraction", count: 12 },
        { category: "enrichment", count: 5 },
      ],
    } as unknown as ReturnType<typeof usePublicCategories>);
    const onPick = vi.fn();

    render(<TrendingMarquee onPick={onPick} />);
    const chip = screen.getByRole("button", { name: /extraction/i });
    expect(chip).toBeInTheDocument();
    fireEvent.click(chip);
    expect(onPick).toHaveBeenCalledWith("extraction");
  });

  it("renders nothing when there are no categories", () => {
    vi.mocked(usePublicCategories).mockReturnValue({
      data: [],
    } as unknown as ReturnType<typeof usePublicCategories>);
    const { container } = render(<TrendingMarquee onPick={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
