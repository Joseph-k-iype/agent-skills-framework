/** Standard response envelope mirrored from the backend (PRD §06). */
export interface ApiResponse<T> {
  success: true;
  data: T;
  meta: Record<string, unknown>;
  errors: unknown[];
}

export interface ApiErrorBody {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
    trace_id?: string;
  };
}

export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}
