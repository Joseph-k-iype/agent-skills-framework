import axios, { AxiosError } from "axios";
import type { ApiErrorBody, ApiResponse } from "./types";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export const http = axios.create({ baseURL, timeout: 30000 });

/** Attach the access token from the auth store (set lazily to avoid a cycle). */
let tokenGetter: () => string | null = () => null;
export function registerTokenGetter(fn: () => string | null) {
  tokenGetter = fn;
}

http.interceptors.request.use((config) => {
  const token = tokenGetter();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export class ApiError extends Error {
  code: string;
  details?: unknown;
  status?: number;
  constructor(code: string, message: string, status?: number, details?: unknown) {
    super(message);
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

/** Unwrap the envelope; throw a typed ApiError on failure. */
export async function unwrap<T>(p: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  try {
    const res = await p;
    return res.data.data;
  } catch (e) {
    const err = e as AxiosError<ApiErrorBody>;
    const body = err.response?.data;
    if (body && "error" in body) {
      throw new ApiError(body.error.code, body.error.message, err.response?.status, body.error.details);
    }
    throw new ApiError("NETWORK_ERROR", err.message, err.response?.status);
  }
}
