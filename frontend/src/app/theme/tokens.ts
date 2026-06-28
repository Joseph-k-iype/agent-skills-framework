/**
 * EAKSO design tokens — Swiss-minimal, typography-led, white theme.
 * Tesla Red is the single accent, used sparingly. 8px spacing grid.
 */
export const tokens = {
  color: {
    accent: "#E82127", // Tesla Red — primary accent, used sparingly
    accentHover: "#C81C21",
    accentActive: "#A8181C",

    ink: "#111114", // primary text
    ink2: "#5B5B61", // secondary text
    ink3: "#8A8A90", // tertiary text / placeholders

    canvas: "#FAFAF8", // app background (warm off-white)
    surface: "#FFFFFF", // cards / panels
    line: "#ECECE8", // hairline borders
    lineStrong: "#DEDEDA",

    ok: "#2E7D52",
    warn: "#B7791F",
    bad: "#C0392B",
  },
  space: 8, // base grid unit
  radius: 8,
  maxContentWidth: 1440,
  font: {
    sans: '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    mono: '"SF Mono", "JetBrains Mono", "Fira Code", ui-monospace, monospace',
  },
} as const;
