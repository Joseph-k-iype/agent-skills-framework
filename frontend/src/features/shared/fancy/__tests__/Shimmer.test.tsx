import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Shimmer } from "../Shimmer";

describe("Shimmer", () => {
  it("renders a block with the requested height and role presentation", () => {
    render(<Shimmer height={40} width={120} />);
    const block = screen.getByRole("presentation");
    expect(block.style.height).toBe("40px");
    expect(block.style.width).toBe("120px");
  });

  it("applies the animated class when motion is allowed and drops it under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(false);
    const { rerender } = render(<Shimmer height={10} />);
    expect(screen.getByRole("presentation").className).toContain("fancy-shimmer");
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    rerender(<Shimmer height={10} />);
    expect(screen.getByRole("presentation").className).not.toContain("fancy-shimmer");
  });
});
