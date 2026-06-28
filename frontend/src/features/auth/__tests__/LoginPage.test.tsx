import { App as AntApp } from "antd";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/authStore";
import * as authApi from "../api/authApi";
import LoginPage from "../pages/LoginPage";

const adminUser = {
  id: "u1",
  username: "admin",
  full_name: "Local Administrator",
  email: null,
  role: "admin" as const,
  permissions: ["workspace:read"],
};

function renderLogin() {
  return render(
    <AntApp>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<div>Dashboard screen</div>} />
        </Routes>
      </MemoryRouter>
    </AntApp>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
    vi.restoreAllMocks();
  });

  it("signs in and stores the session, then navigates to the dashboard", async () => {
    vi.spyOn(authApi, "login").mockResolvedValue({
      tokens: { access_token: "acc", refresh_token: "ref", token_type: "bearer" },
      user: adminUser,
    });

    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("admin"), "admin");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "admin");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));

    await waitFor(() => expect(screen.getByText("Dashboard screen")).toBeInTheDocument());
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("acc");
    expect(state.user?.role).toBe("admin");
  });

  it("shows an error and stays on the login page when credentials are rejected", async () => {
    const { ApiError } = await import("@/shared/api/client");
    vi.spyOn(authApi, "login").mockRejectedValue(
      new ApiError("UNAUTHORIZED", "Invalid username or password", 401),
    );

    renderLogin();
    await userEvent.type(screen.getByPlaceholderText("admin"), "admin");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "nope");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));

    await waitFor(() =>
      expect(screen.getByText("Invalid username or password")).toBeInTheDocument(),
    );
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
