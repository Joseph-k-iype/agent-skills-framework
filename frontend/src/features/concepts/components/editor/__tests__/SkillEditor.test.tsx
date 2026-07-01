// frontend/src/features/concepts/components/editor/__tests__/SkillEditor.test.tsx
import { render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { SkillEditor, type SkillEditorHandle } from "../SkillEditor";
import { toggleBold } from "@/features/concepts/lib/markdownTransforms";

// Monaco does not run in jsdom — replace it with a controlled <textarea>.
vi.mock("@monaco-editor/react", () => ({
  default: ({ value, onChange }: { value: string; onChange: (v?: string) => void }) => (
    <textarea aria-label="monaco" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

describe("SkillEditor", () => {
  it("renders the (mocked) editor with the given value", () => {
    render(<SkillEditor value={"hello"} onChange={() => {}} />);
    expect(screen.getByLabelText("monaco")).toHaveValue("hello");
  });

  it("applyTransform runs a transform against the current value and emits onChange", () => {
    const onChange = vi.fn();
    const ref = createRef<SkillEditorHandle>();
    render(<SkillEditor ref={ref} value={"word"} onChange={onChange} />);
    ref.current!.applyTransform(toggleBold);
    // With no live Monaco selection the fallback selects the whole document.
    expect(onChange).toHaveBeenCalledWith("**word**");
  });
});
