import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { GradientText } from "../GradientText";

describe("GradientText", () => {
  it("renders the headline text", () => {
    render(<GradientText>Find a data skill</GradientText>);
    expect(screen.getByText("Find a data skill")).toBeInTheDocument();
  });

  it("uses the animated gradient class when motion is allowed", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(false);
    render(<GradientText>Hi</GradientText>);
    expect(screen.getByText("Hi").className).toContain("fancy-gradient");
  });

  it("renders solid ink (no gradient class) under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(<GradientText>Hi</GradientText>);
    const el = screen.getByText("Hi");
    expect(el.className).not.toContain("fancy-gradient");
    expect(el.style.color).not.toBe("");
  });
});
