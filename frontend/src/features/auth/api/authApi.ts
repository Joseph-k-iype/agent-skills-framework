import { http, unwrap } from "@/shared/api/client";
import type { UserProfile } from "@/stores/authStore";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface LoginResponse {
  tokens: TokenPair;
  user: UserProfile;
}

export function login(username: string, password: string) {
  return unwrap<LoginResponse>(http.post("/auth/login", { username, password }));
}

export function fetchMe() {
  return unwrap<UserProfile>(http.get("/auth/me"));
}

export function refreshTokens(refresh_token: string) {
  return unwrap<TokenPair>(http.post("/auth/refresh", { refresh_token }));
}
