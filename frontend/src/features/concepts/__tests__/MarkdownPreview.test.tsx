import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MarkdownPreview } from "../components/MarkdownPreview";

const renderMock = vi.fn().mockResolvedValue({ svg: "<svg id='ok'></svg>" });

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: (...args: unknown[]) => renderMock(...args),
  },
}));

describe("MarkdownPreview", () => {
  it("renders markdown headings", () => {
    render(<MarkdownPreview source={"# Hello World"} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Hello World");
  });

  it("renders a mermaid fence via mermaid.render", async () => {
    const md = "```mermaid\nflowchart LR\n A --> B\n```";
    render(<MarkdownPreview source={md} />);
    await waitFor(() => expect(renderMock).toHaveBeenCalled());
    const call = renderMock.mock.calls[0];
    expect(String(call[1])).toContain("flowchart LR");
  });

  it("renders regular code blocks as code, not diagrams", () => {
    const md = "```python\nx = 1\n```";
    render(<MarkdownPreview source={md} />);
    expect(screen.queryByTestId("mermaid")).toBeNull();
  });
});
