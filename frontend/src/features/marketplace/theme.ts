/** Per-category accent colors — muted, desaturated wayfinding hues. Tesla
 * Red is reserved exclusively for the featured tick, so none of these may
 * be red or near `tokens.color.accent` (#E82127). */
export const CATEGORY_ACCENT: Record<string, string> = {
  transformation: "#3B5BA9",
  enrichment: "#2E7D6B",
  validation: "#4B7A3F",
  extraction: "#B07A2E",
  prompt: "#6B4FA0",
  toolkit: "#4A4A52",
};

export function categoryAccentFor(category?: string | null): string {
  return CATEGORY_ACCENT[(category ?? "").toLowerCase()] ?? "#8A8A90";
}
