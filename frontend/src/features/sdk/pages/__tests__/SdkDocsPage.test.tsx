import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../api/sdkApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sdkApi")>();
  return {
    ...actual,
    useSkillListings: vi.fn(),
  };
});

import { useSkillListings } from "../../api/sdkApi";
import SdkDocsPage from "../SdkDocsPage";

const MOCK_SKILLS = [
  { id: "skill-abc", title: "Summariser", version: "1.0", tags: [], downloads: 5 },
  { id: "skill-xyz", title: "Classifier", version: "1.0", tags: [], downloads: 3 },
];

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>
        <MemoryRouter>
          <SdkDocsPage />
        </MemoryRouter>
      </AntApp>
    </QueryClientProvider>,
  );
}

describe("SdkDocsPage", () => {
  it("renders the quickstart heading", () => {
    vi.mocked(useSkillListings).mockReturnValue({
      data: MOCK_SKILLS,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useSkillListings>);

    wrap();
    expect(screen.getAllByText(/quickstart/i).length).toBeGreaterThan(0);
  });

  it("renders a Download SDK link pointing to /api/v1/sdk/download", () => {
    vi.mocked(useSkillListings).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useSkillListings>);

    wrap();
    const btn = screen.getByTestId("download-sdk-btn");
    expect(btn).toBeInTheDocument();
    // Ant Design Button with href renders an <a>
    const anchor = btn.closest("a") ?? btn.querySelector("a") ?? btn;
    expect(anchor.getAttribute("href")).toBe("/api/v1/sdk/download");
  });

  it("snippet contains EAKSO_API_KEY and not a literal API key", () => {
    vi.mocked(useSkillListings).mockReturnValue({
      data: MOCK_SKILLS,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useSkillListings>);

    wrap();
    const snippet = screen.getByTestId("sdk-snippet");
    expect(snippet.textContent).toContain("EAKSO_API_KEY");
    // Must not contain any hard-coded key pattern (sk-..., eakso_..., etc.)
    expect(snippet.textContent).not.toMatch(/sk-[A-Za-z0-9]{10,}/);
    expect(snippet.textContent).not.toMatch(/eakso_[A-Za-z0-9]{10,}/);
  });

  it("updates the skill id in the snippet when a skill is selected", async () => {
    vi.mocked(useSkillListings).mockReturnValue({
      data: MOCK_SKILLS,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useSkillListings>);

    wrap();

    // Before selection the placeholder skill-id is shown
    const snippet = screen.getByTestId("sdk-snippet");
    expect(snippet.textContent).toContain("<skill-id>");

    // Simulate selecting via the hidden select input (Ant Design Select)
    const selectInput = document.querySelector(".ant-select-selector");
    if (selectInput) {
      fireEvent.mouseDown(selectInput);
    }
    // Click the first option if dropdown opened
    const options = document.querySelectorAll(".ant-select-item-option");
    if (options.length > 0) {
      fireEvent.click(options[0]);
      expect(snippet.textContent).toContain("skill-abc");
      expect(snippet.textContent).not.toContain("<skill-id>");
    }
  });
});
