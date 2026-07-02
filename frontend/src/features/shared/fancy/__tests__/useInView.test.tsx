import { render, screen } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useInView } from "../useInView";

const originalIO = globalThis.IntersectionObserver;
afterEach(() => {
  globalThis.IntersectionObserver = originalIO;
  vi.restoreAllMocks();
});

function Probe() {
  const [ref, inView] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} data-testid="probe">
      {inView ? "in" : "out"}
    </div>
  );
}

describe("useInView", () => {
  it("flips inView to true when the observer reports an intersection", () => {
    let captured: ((entries: { isIntersecting: boolean }[]) => void) | null = null;
    const observe = vi.fn();
    const disconnect = vi.fn();
    globalThis.IntersectionObserver = vi
      .fn()
      .mockImplementation((cb: (entries: { isIntersecting: boolean }[]) => void) => {
        captured = cb;
        return { observe, disconnect, unobserve: vi.fn(), takeRecords: vi.fn() };
      }) as unknown as typeof IntersectionObserver;

    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("out");
    expect(observe).toHaveBeenCalledTimes(1);
    act(() => {
      captured?.([{ isIntersecting: true }]);
    });
    expect(screen.getByTestId("probe")).toHaveTextContent("in");
  });

  it("reports inView=true immediately when IntersectionObserver is undefined", () => {
    // @ts-expect-error simulate jsdom/SSR without IO
    globalThis.IntersectionObserver = undefined;
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("in");
  });
});
