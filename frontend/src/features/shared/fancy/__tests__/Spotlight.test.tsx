import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../usePrefersReducedMotion", () => ({
  usePrefersReducedMotion: vi.fn(() => false),
}));

import { usePrefersReducedMotion } from "../usePrefersReducedMotion";
import { Spotlight } from "../Spotlight";

describe("Spotlight", () => {
  it("renders its children", () => {
    render(
      <Spotlight>
        <div data-testid="card">card</div>
      </Spotlight>,
    );
    expect(screen.getByTestId("card")).toBeInTheDocument();
  });

  it("sets the --mx/--my custom properties on pointer move when motion is allowed", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(false);
    render(
      <Spotlight>
        <div data-testid="card">card</div>
      </Spotlight>,
    );
    const wrap = screen.getByTestId("card").parentElement as HTMLElement;
    fireEvent.pointerMove(wrap, { clientX: 30, clientY: 20 });
    expect(wrap.style.getPropertyValue("--mx")).not.toBe("");
    expect(wrap.style.getPropertyValue("--my")).not.toBe("");
  });

  it("does not set custom properties under reduced motion", () => {
    vi.mocked(usePrefersReducedMotion).mockReturnValue(true);
    render(
      <Spotlight>
        <div data-testid="card">card</div>
      </Spotlight>,
    );
    const wrap = screen.getByTestId("card").parentElement as HTMLElement;
    fireEvent.pointerMove(wrap, { clientX: 30, clientY: 20 });
    expect(wrap.style.getPropertyValue("--mx")).toBe("");
  });
});
