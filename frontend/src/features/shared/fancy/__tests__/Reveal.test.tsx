import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => true),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Reveal } from "../Reveal";

describe("Reveal", () => {
  it("renders its children", () => {
    render(<Reveal>hello reveal</Reveal>);
    expect(screen.getByText("hello reveal")).toBeInTheDocument();
  });

  it("renders visible (opacity 1, no transform) under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Reveal>
        <span data-testid="kid">x</span>
      </Reveal>,
    );
    const wrapper = screen.getByTestId("kid").parentElement as HTMLElement;
    expect(wrapper.style.opacity).toBe("1");
    expect(wrapper.style.transform).toBe("none");
  });
});
