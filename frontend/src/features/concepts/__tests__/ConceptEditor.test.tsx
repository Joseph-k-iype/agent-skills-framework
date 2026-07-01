import { App } from "antd";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("mermaid", () => ({
  default: { initialize: vi.fn(), render: vi.fn().mockResolvedValue({ svg: "<svg></svg>" }) },
}));

vi.mock("@monaco-editor/react", () => ({
  default: ({ value, onChange }: { value: string; onChange: (v?: string) => void }) => (
    <textarea aria-label="monaco" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

const { updateMutate } = vi.hoisted(() => ({ updateMutate: vi.fn().mockResolvedValue({}) }));

vi.mock("../api/taxonomyApi", () => ({
  useTaxonomyTerms: () => ({ isLoading: false, data: { terms: [] } }),
}));

vi.mock("../api/conceptApi", () => {
  // Stable references — mirrors react-query's identity stability between renders.
  const data = {
    workspace_id: "w1",
    path: "finance/invoice-ocr.md",
    type: "skill",
    title: "Invoice OCR",
    description: "Extracts line items",
    runtime: "python 3.12",
    tags: ["finance"],
    capabilities: [],
    sources: ["internal"],
    parent_path: null,
    body: "# Original",
    frontmatter: {},
    links: [],
    references: [],
  };
  const update = { isPending: false, mutateAsync: updateMutate };
  return {
    useConcept: () => ({ isLoading: false, data }),
    useConcepts: () => ({ isLoading: false, data: [data, { ...data, path: "x/other.md", title: "Other", runtime: "node 20" }] }),
    useConceptHistory: () => ({ data: [] }),
    useUpdateConcept: () => update,
    useEvaluateConcept: () => ({ isPending: false, mutate: vi.fn(), data: undefined }),
    useDeepEvaluateConcept: () => ({ isPending: false, mutate: vi.fn(), data: undefined }),
  };
});

function renderEditor() {
  return render(
    <App>
      <MemoryRouter initialEntries={["/concepts/w1/finance/invoice-ocr.md"]}>
        <Routes>
          <Route
            path="/concepts/:workspaceId/*"
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            element={<EditorWrapper />}
          />
        </Routes>
      </MemoryRouter>
    </App>,
  );
}

// Lazy import to ensure mocks are applied first.
import ConceptEditorPage from "../pages/ConceptEditorPage";
function EditorWrapper() {
  return <ConceptEditorPage />;
}

describe("ConceptEditorPage", () => {
  it("does not show an OKF References tab", () => {
    renderEditor();
    expect(screen.queryByText(/OKF References/i)).toBeNull();
  });

  it("runtime field accepts arbitrary free text", async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.click(screen.getByRole("tab", { name: /Metadata/i }));
    // The runtime field is a free-text AutoComplete pre-filled from the concept.
    const runtime = await screen.findByDisplayValue("python 3.12");
    await user.clear(runtime);
    await user.type(runtime, "rust 1.79 + wasm");
    expect(runtime).toHaveValue("rust 1.79 + wasm");
  });

  it("typing in the body updates the live preview", async () => {
    const user = userEvent.setup();
    renderEditor();
    const body = screen.getByLabelText("monaco");
    await user.clear(body);
    await user.type(body, "# Hello Preview");
    expect(screen.getByRole("heading", { name: "Hello Preview" })).toBeInTheDocument();
  });

  it("save payload includes sources and parent_path", async () => {
    const user = userEvent.setup();
    renderEditor();
    // Visit Metadata tab so its form fields mount and are registered with AntD Form.
    await user.click(screen.getByRole("tab", { name: /Metadata/i }));
    const saveBtn = screen.getByRole("button", { name: /Save/i });
    await user.click(saveBtn);
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ sources: ["internal"], parent_path: null }),
    );
  });
});
