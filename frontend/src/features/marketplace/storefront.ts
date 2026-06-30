import type { CSSProperties } from "react";
import { tokens } from "@/app/theme/tokens";

/**
 * Storefront Swiss design constants — single source of truth shared by
 * SkillCard, the marketplace home grid, and the listing detail page.
 *
 * Rules encoded here (see Storefront Swiss Uplift spec):
 * - Tesla Red (`tokens.color.accent`) is the ONLY accent and is reserved for
 *   functional markers (e.g. the "featured" tick) — never a fill/band/decoration.
 * - Category color is demoted to a single small square swatch; no full-width
 *   color bands or gradients.
 * - No serif anywhere. Titles use `tokens.font.sans` at weight 600 with tight
 *   tracking. All data values (SHA, counts, category code) use `tokens.font.mono`.
 * - Surfaces are flat: 4px radius, 1px hairline border, no drop shadow.
 */

/** Corner radius for storefront surfaces (cards, chips, swatches). */
export const RADIUS = 4;

/** Grid gutter / masonry column gap used across the storefront layout. */
export const GUTTER = 24;

/** Side length of the category color swatch (the only color outside ink/accent). */
export const SWATCH = 8;

/** Shared type scale for storefront surfaces. */
export const storefrontType = {
  title: {
    font: `600 16px/1.3 ${tokens.font.sans}`,
    letterSpacing: "-0.02em",
    color: tokens.color.ink,
  } satisfies CSSProperties,
  eyebrow: {
    font: `600 10px/1 ${tokens.font.mono}`,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: tokens.color.ink3,
  } satisfies CSSProperties,
  body: {
    font: `400 13px/1.55 ${tokens.font.sans}`,
    color: tokens.color.ink2,
  } satisfies CSSProperties,
  mono: {
    font: `500 11px/1.4 ${tokens.font.mono}`,
    color: tokens.color.ink3,
  } satisfies CSSProperties,
  monoSmall: {
    font: `500 10px/1.4 ${tokens.font.mono}`,
    color: tokens.color.ink3,
  } satisfies CSSProperties,
} as const;

/** Hairline card border — flat, no shadow. Pass `hover: true` for the darkened state. */
export function cardBorder(hover = false): string {
  return `1px solid ${hover ? tokens.color.lineStrong : tokens.color.line}`;
}

/** Small flat color swatch style (the one allowed non-ink/accent color source). */
export function swatchStyle(color: string): CSSProperties {
  return {
    display: "inline-block",
    width: SWATCH,
    height: SWATCH,
    borderRadius: 1,
    background: color,
    flexShrink: 0,
  };
}
