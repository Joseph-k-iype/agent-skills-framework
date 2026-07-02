import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Marquee } from "../Marquee";

describe("Marquee", () => {
  it("duplicates its track so the loop is seamless (children rendered twice)", () => {
    render(
      <Marquee>
        <span>trending-tag</span>
      </Marquee>,
    );
    // One copy in the real track, one in the aria-hidden clone.
    expect(screen.getAllByText("trending-tag")).toHaveLength(2);
  });

  it("renders a static, scrollable row (no animation class) under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Marquee>
        <span>chip</span>
      </Marquee>,
    );
    // Under reduced motion we still duplicate is unnecessary: render once, no track class.
    const tracks = document.querySelectorAll(".fancy-marquee-track");
    expect(tracks).toHaveLength(0);
    expect(screen.getByText("chip")).toBeInTheDocument();
  });
});
