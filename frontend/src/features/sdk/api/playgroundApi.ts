const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export interface SkillResponse {
  id: string;
  source_path: string;
  title: string;
  type: string | null;
  version: string;
  content: string;
  body: string | null;
  system_prompt: string | null;
}

/**
 * Call the SDK skill endpoint with the user-supplied API key as Bearer.
 * Does NOT use the app's JWT-injecting axios instance — raw fetch only.
 * Throws with status 401 (or other non-ok status) so the caller can surface it.
 */
export async function fetchSkillWithKey(
  listingId: string,
  apiKey: string,
): Promise<SkillResponse> {
  const url = `${API_BASE}/sdk/skill/${encodeURIComponent(listingId)}`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.error?.message) detail = body.error.message;
      else if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore JSON parse failure; keep generic message
    }
    const err = new Error(detail);
    (err as Error & { status: number }).status = res.status;
    throw err;
  }

  // The backend wraps responses in { success, data, meta, errors }
  const envelope = await res.json();
  return envelope.data ?? envelope;
}
