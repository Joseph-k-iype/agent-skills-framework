import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Role = "consumer" | "developer" | "admin";

export interface UserProfile {
  id: string;
  username: string;
  full_name: string | null;
  email: string | null;
  role: Role;
  permissions: string[];
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
  setSession: (access: string, refresh: string, user: UserProfile) => void;
  setUser: (user: UserProfile) => void;
  clear: () => void;
  hasPermission: (code: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setSession: (accessToken, refreshToken, user) => set({ accessToken, refreshToken, user }),
      setUser: (user) => set({ user }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
      hasPermission: (code) => {
        const u = get().user;
        if (!u) return false;
        return u.permissions.includes(code);
      },
    }),
    { name: "eakso-auth" },
  ),
);
