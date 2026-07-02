import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Magnetic } from "../Magnetic";

describe("Magnetic", () => {
  it("renders its children", () => {
    render(
      <Magnetic>
        <button type="button">Go</button>
      </Magnetic>,
    );
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });

  it("does not transform under reduced motion (pointer handler is a no-op)", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Magnetic>
        <span data-testid="kid">x</span>
      </Magnetic>,
    );
    const wrap = screen.getByTestId("kid").parentElement as HTMLElement;
    fireEvent.pointerMove(wrap, { clientX: 50, clientY: 50 });
    expect(wrap.style.transform === "" || wrap.style.transform === "none").toBe(true);
  });
});
