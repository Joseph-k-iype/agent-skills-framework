import type { CSSProperties, ReactNode } from "react";
import { tokens } from "@/app/theme/tokens";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Headline with an animated gradient (background-clip: text). Reduced motion →
 * solid `tokens.color.ink`, no animation.
 */
export function GradientText({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  const reduced = usePrefersReducedMotion();
  if (reduced) {
    return <span style={{ color: tokens.color.ink, ...style }}>{children}</span>;
  }
  return (
    <span
      className="fancy-gradient"
      style={{
        backgroundImage: `linear-gradient(90deg, ${tokens.color.ink} 0%, ${tokens.color.accent} 50%, ${tokens.color.ink} 100%)`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        WebkitTextFillColor: "transparent",
        ...style,
      }}
    >
      {children}
    </span>
  );
}

export default GradientText;
