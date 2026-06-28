import { useEffect, useState, type ReactNode } from "react";
import { registerTokenGetter } from "@/shared/api/client";
import { useAuthStore } from "@/stores/authStore";
import { fetchMe } from "@/features/auth/api/authApi";

/**
 * Wires the access token into the axios client and revalidates the stored
 * session against /me on boot (so a stale token logs the user out cleanly).
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const clear = useAuthStore((s) => s.clear);

  // Register once so interceptors can read the latest token.
  useEffect(() => {
    registerTokenGetter(() => useAuthStore.getState().accessToken);
  }, []);

  useEffect(() => {
    let active = true;
    if (!accessToken) {
      setReady(true);
      return;
    }
    fetchMe()
      .then((u) => active && setUser(u))
      .catch(() => active && clear())
      .finally(() => active && setReady(true));
    return () => {
      active = false;
    };
    // Run once on mount; token changes after login are handled by setSession.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}
