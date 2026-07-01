// frontend/src/features/shared/fancy/__tests__/NumberTicker.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NumberTicker } from "../NumberTicker";

describe("NumberTicker", () => {
  it("renders the target value as text", () => {
    render(<NumberTicker value={42} />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});
