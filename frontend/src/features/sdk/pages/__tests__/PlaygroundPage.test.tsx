import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock the playground API (raw fetch wrapper)
vi.mock("../../api/playgroundApi", () => ({
  fetchSkillWithKey: vi.fn(),
}));

// Mock the sdk listings hook
vi.mock("../../api/sdkApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sdkApi")>();
  return { ...actual, useSkillListings: vi.fn() };
});

// Mock the api keys hooks
vi.mock("@/features/settings/api/apiKeysApi", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/features/settings/api/apiKeysApi")>();
  return { ...actual, useApiKeys: vi.fn(), useKeyUsage: vi.fn() };
});

import { fetchSkillWithKey } from "../../api/playgroundApi";
import { useSkillListings } from "../../api/sdkApi";
import { useApiKeys, useKeyUsage } from "@/features/settings/api/apiKeysApi";
import PlaygroundPage from "../PlaygroundPage";

const MOCK_SKILLS = [
  { id: "skill-abc", title: "Summariser", version: "1.0", tags: [], downloads: 5 },
];

const MOCK_KEYS = [{ id: "key-1", name: "My Key", prefix: "sk_live_abc" }];

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>
        <MemoryRouter>
          <PlaygroundPage />
        </MemoryRouter>
      </AntApp>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(useSkillListings).mockReturnValue({
    data: MOCK_SKILLS,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useSkillListings>);

  vi.mocked(useApiKeys).mockReturnValue({
    data: MOCK_KEYS,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useApiKeys>);

  vi.mocked(useKeyUsage).mockReturnValue({
    data: { total: 1, last_used_at: null, by_kind: {}, by_skill: [], recent: [] },
    isLoading: false,
    isError: false,
    refetch: vi.fn().mockResolvedValue(undefined),
  } as unknown as ReturnType<typeof useKeyUsage>);
});

describe("PlaygroundPage", () => {
  it("renders the page heading", () => {
    wrap();
    expect(screen.getByText(/test your key/i)).toBeInTheDocument();
  });

  it("renders an API key input and a Run button", () => {
    wrap();
    expect(screen.getByPlaceholderText(/sk_live_/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run/i })).toBeInTheDocument();
  });

  it("shows skill response and usage-recorded indicator on mocked 200", async () => {
    vi.mocked(fetchSkillWithKey).mockResolvedValue({
      id: "skill-abc",
      source_path: "skills/summariser.md",
      title: "Summariser",
      type: "skill",
      version: "1.0",
      content: "## Summariser content",
      body: null,
      system_prompt: "You are a summariser.",
    });

    wrap();

    // Enter API key
    const keyInput = screen.getByPlaceholderText(/sk_live_/i);
    fireEvent.change(keyInput, { target: { value: "sk_live_testkey123" } });

    // Select a skill via the select dropdown
    const selectEl = document.querySelector(".ant-select-selector");
    if (selectEl) fireEvent.mouseDown(selectEl);
    const options = document.querySelectorAll(".ant-select-item-option");
    if (options.length > 0) fireEvent.click(options[0]);

    // Click Run
    fireEvent.click(screen.getByRole("button", { name: /run/i }));

    // Response content appears
    await waitFor(() => {
      expect(screen.getByTestId("playground-response")).toBeInTheDocument();
    });
    expect(screen.getByTestId("playground-response").textContent).toContain(
      "You are a summariser.",
    );

    // Usage recorded indicator
    await waitFor(() => {
      expect(screen.getByTestId("usage-recorded")).toBeInTheDocument();
    });
  });

  it("shows error notice and no success UI on mocked 401", async () => {
    const err = Object.assign(new Error("Invalid or revoked API key"), { status: 401 });
    vi.mocked(fetchSkillWithKey).mockRejectedValue(err);

    wrap();

    const keyInput = screen.getByPlaceholderText(/sk_live_/i);
    fireEvent.change(keyInput, { target: { value: "sk_live_bad" } });

    const selectEl = document.querySelector(".ant-select-selector");
    if (selectEl) fireEvent.mouseDown(selectEl);
    const options = document.querySelectorAll(".ant-select-item-option");
    if (options.length > 0) fireEvent.click(options[0]);

    fireEvent.click(screen.getByRole("button", { name: /run/i }));

    await waitFor(() => {
      expect(screen.getByTestId("playground-error")).toBeInTheDocument();
    });
    expect(screen.getByTestId("playground-error").textContent).toContain("401");

    // No success UI shown
    expect(screen.queryByTestId("playground-response")).not.toBeInTheDocument();
    expect(screen.queryByTestId("usage-recorded")).not.toBeInTheDocument();
  });
});
