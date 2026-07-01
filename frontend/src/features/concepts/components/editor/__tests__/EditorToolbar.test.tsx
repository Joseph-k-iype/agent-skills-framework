// frontend/src/features/concepts/components/editor/__tests__/EditorToolbar.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EditorToolbar } from "../EditorToolbar";
import type { Transform } from "@/features/concepts/lib/markdownTransforms";

describe("EditorToolbar", () => {
  it("applies bold when the Bold button is clicked", async () => {
    const onApply = vi.fn();
    render(<EditorToolbar onApply={onApply} onInsertConceptLink={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /bold/i }));
    const t = onApply.mock.calls[0][0] as Transform;
    expect(t("word", { start: 0, end: 4 }).text).toBe("**word**");
  });

  it("opens the concept-link modal via its callback", async () => {
    const onLink = vi.fn();
    render(<EditorToolbar onApply={() => {}} onInsertConceptLink={onLink} />);
    await userEvent.click(screen.getByRole("button", { name: /link concept/i }));
    expect(onLink).toHaveBeenCalled();
  });
});
