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

  it("renders allowed inline HTML (details/summary)", () => {
    render(<MarkdownPreview source={"<details><summary>More</summary>body</details>"} />);
    expect(screen.getByText("More")).toBeInTheDocument();
  });

  it("strips <script> tags from embedded HTML", () => {
    const { container } = render(
      <MarkdownPreview source={"<p>hi</p><script>window.__pwned=1</script>"} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });

  it("drops javascript: links", () => {
    const { container } = render(<MarkdownPreview source={"[x](javascript:alert(1))"} />);
    const a = container.querySelector("a");
    expect(a?.getAttribute("href") ?? "").not.toContain("javascript:");
  });

  it("removes iframes whose src host is not allow-listed", () => {
    const { container } = render(
      <MarkdownPreview source={'<iframe src="https://evil.example/x"></iframe>'} />,
    );
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("keeps iframes from an allow-listed host", () => {
    const { container } = render(
      <MarkdownPreview source={'<iframe src="https://www.youtube.com/embed/abc"></iframe>'} />,
    );
    expect(container.querySelector("iframe")).not.toBeNull();
  });
});
