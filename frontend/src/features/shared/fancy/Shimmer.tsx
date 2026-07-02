import { tokens } from "@/app/theme/tokens";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Animated skeleton block (moving gradient). Reduced motion → flat neutral
 * block. Used as the loading placeholder for the leaderboard and grid tail.
 */
export function Shimmer({
  height,
  width = "100%",
  radius = 4,
}: {
  height: number | string;
  width?: number | string;
  radius?: number;
}) {
  const reduced = usePrefersReducedMotion();
  return (
    <div
      role="presentation"
      className={reduced ? undefined : "fancy-shimmer"}
      style={{
        height: typeof height === "number" ? `${height}px` : height,
        width: typeof width === "number" ? `${width}px` : width,
        borderRadius: radius,
        background: reduced
          ? tokens.color.line
          : `linear-gradient(90deg, ${tokens.color.line} 0%, ${tokens.color.canvas} 50%, ${tokens.color.line} 100%)`,
      }}
    />
  );
}

export default Shimmer;
