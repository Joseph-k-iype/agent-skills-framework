import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const navigate = vi.fn();
vi.mock("react-router-dom", () => ({ useNavigate: () => navigate }));

vi.mock("@/features/workspace/api/workspaceApi", () => ({
  useWorkspaces: vi.fn(),
}));

vi.mock("../../api/marketplaceApi", () => ({
  useCloneListing: vi.fn(),
}));

vi.mock("@/stores/authStore", () => ({
  useAuthStore: (sel: (s: unknown) => unknown) => sel({ user: mockUser }),
}));

import { useWorkspaces } from "@/features/workspace/api/workspaceApi";
import { useAuthStore } from "@/stores/authStore";
import { useCloneListing } from "../../api/marketplaceApi";
import { CloneModal } from "../CloneModal";

let mockUser: unknown = { id: "u1", username: "dev", permissions: ["skill:create"] };

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>{ui}</AntApp>
    </QueryClientProvider>,
  );
}

describe("CloneModal", () => {
  it("submitting calls the mutation with workspace_id, folder_path, name, version", async () => {
    mockUser = { id: "u1", username: "dev", permissions: ["skill:create"] };
    void useAuthStore;
    const mutate = vi.fn();
    vi.mocked(useCloneListing).mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useCloneListing>);
    vi.mocked(useWorkspaces).mockReturnValue({
      data: [{ id: "ws1", name: "Ops" }],
    } as unknown as ReturnType<typeof useWorkspaces>);

    wrap(
      <CloneModal
        open
        listingId="lid-1"
        listingTitle="My Skill"
        versions={[{ version: 2, sha: "abc", changelog: null, created_at: null }]}
        onClose={() => {}}
      />,
    );

    const user = userEvent.setup();
    // pick the workspace (first combobox is the workspace select)
    await user.click(screen.getAllByRole("combobox")[0]);
    await user.click(await screen.findByText("Ops"));

    await user.click(screen.getByRole("button", { name: /clone/i }));

    await waitFor(() => expect(mutate).toHaveBeenCalled());
    const body = mutate.mock.calls[0][0];
    expect(body).toMatchObject({ workspace_id: "ws1" });
    expect(body).toHaveProperty("folder_path");
    expect(body).toHaveProperty("name");
    expect(body).toHaveProperty("version");
  });

  it("redirects unauthenticated users to /login?next=", () => {
    mockUser = null;
    vi.mocked(useCloneListing).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCloneListing>);
    vi.mocked(useWorkspaces).mockReturnValue({
      data: [],
    } as unknown as ReturnType<typeof useWorkspaces>);

    wrap(
      <CloneModal
        open
        listingId="lid-1"
        listingTitle="My Skill"
        versions={[]}
        onClose={() => {}}
      />,
    );

    expect(navigate).toHaveBeenCalledWith("/login?next=/marketplace/lid-1");
  });
});
