import { App as AntApp } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/stores/authStore";
import { PublicLayout } from "../PublicLayout";

const adminUser = {
  id: "u1",
  username: "admin",
  full_name: "Local Administrator",
  email: null,
  role: "admin" as const,
  permissions: [],
};

function renderPublic() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AntApp>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route element={<PublicLayout />}>
              <Route index element={<div>Home content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AntApp>
    </QueryClientProvider>,
  );
}

describe("PublicLayout", () => {
  beforeEach(() => useAuthStore.getState().clear());
  afterEach(() => useAuthStore.getState().clear());

  it("shows Sign in (and no Dashboard) when logged out", () => {
    renderPublic();
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
    expect(screen.queryByText(/dashboard/i)).not.toBeInTheDocument();
  });

  it("shows the account name + Dashboard and hides Sign in when logged in", () => {
    useAuthStore.setState({ accessToken: "t", user: adminUser });
    renderPublic();
    expect(screen.queryByText(/sign in/i)).not.toBeInTheDocument();
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
    // From the reused UserMenu — account identity stays visible on the public surface.
    expect(screen.getByText("Local Administrator")).toBeInTheDocument();
  });
});
