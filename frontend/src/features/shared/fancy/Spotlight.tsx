import type { ReactNode } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import { tokens } from "@/app/theme/tokens";

/**
 * Tracks the cursor via `--mx`/`--my` custom properties and paints a soft radial
 * highlight over the child on hover. Reduced motion → no highlight (passthrough).
 */
export function Spotlight({ children }: { children: ReactNode }) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return <div>{children}</div>;
  }

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    el.style.setProperty("--my", `${e.clientY - rect.top}px`);
  };

  return (
    <div
      onPointerMove={onPointerMove}
      style={{
        position: "relative",
        borderRadius: 4,
        // Soft radial highlight anchored at the cursor; transparent until hovered.
        backgroundImage: `radial-gradient(180px circle at var(--mx, 50%) var(--my, 50%), ${tokens.color.line} 0%, transparent 60%)`,
      }}
    >
      {children}
    </div>
  );
}

export default Spotlight;
