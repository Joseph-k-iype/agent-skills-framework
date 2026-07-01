import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { http } from "@/shared/api/client";
import { TaxonomyPicker } from "../TaxonomyPicker";

// Mock the http client so tests never make real network calls.
vi.mock("@/shared/api/client", () => ({
  http: {
    get: vi.fn(),
  },
  unwrap: vi.fn(async (p) => {
    const res = await p;
    return res.data.data;
  }),
}));

const mockTerms = [
  { key: "extraction", label: "Extraction", description: "Data extraction skills", status: "active", parent_key: null },
  { key: "extraction:invoice", label: "Invoice Extraction", description: "Invoice parsing", status: "active", parent_key: "extraction" },
  { key: "classification", label: "Classification", description: "Classification skills", status: "active", parent_key: null },
];

function renderPicker(props: {
  kind: "capability" | "source";
  value?: string[];
  onChange?: (v: string[]) => void;
}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>
        <MemoryRouter>
          <TaxonomyPicker {...props} />
        </MemoryRouter>
      </AntApp>
    </QueryClientProvider>,
  );
}

describe("TaxonomyPicker", () => {
  beforeEach(() => {
    vi.mocked(http.get).mockResolvedValue({
      data: { data: { terms: mockTerms } },
    });
  });

  it("renders options seeded from the taxonomy API", async () => {
    renderPicker({ kind: "capability", value: [], onChange: vi.fn() });

    // The select should be present
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();

    // Open the dropdown
    await userEvent.click(select);

    // Wait for the taxonomy terms to appear as options
    await waitFor(() => {
      expect(screen.getByTitle("Extraction")).toBeInTheDocument();
    });
    expect(screen.getByTitle("Invoice Extraction")).toBeInTheDocument();
    expect(screen.getByTitle("Classification")).toBeInTheDocument();
  });

  it("calls onChange with a canonical term key when a known option is selected", async () => {
    const onChange = vi.fn();
    renderPicker({ kind: "capability", value: [], onChange });

    const select = screen.getByRole("combobox");
    await userEvent.click(select);

    await waitFor(() => {
      expect(screen.getByTitle("Extraction")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByTitle("Extraction"));

    // AntD Select mode="tags" calls onChange(values, options) — check only the values arg.
    expect(onChange).toHaveBeenCalledWith(["extraction"], expect.anything());
  });

  it("allows a free entry (value not in the taxonomy list)", async () => {
    const onChange = vi.fn();
    renderPicker({ kind: "capability", value: [], onChange });

    // AntD Select renders an <input> inside the combobox wrapper — type into that.
    const input = screen.getByRole("combobox");
    await userEvent.click(input);
    await userEvent.type(input, "my-custom-term");

    // AntD renders the typed value as a selectable option in the dropdown list.
    await waitFor(() => {
      expect(screen.getByTitle("my-custom-term")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTitle("my-custom-term"));

    await waitFor(() => {
      // AntD Select mode="tags" calls onChange(values, options) — check only the values arg.
      expect(onChange).toHaveBeenCalledWith(["my-custom-term"], expect.anything());
    });
  });
});
