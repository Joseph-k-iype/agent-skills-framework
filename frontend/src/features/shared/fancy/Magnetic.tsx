import { useRef, type ReactNode } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

/**
 * Translates its child toward the cursor within its bounds (rAF-eased) and
 * springs back on leave. Reduced motion → passthrough, no transform.
 */
export function Magnetic({
  children,
  strength = 0.3,
}: {
  children: ReactNode;
  strength?: number;
}) {
  const reduced = usePrefersReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const raf = useRef(0);

  const apply = (x: number, y: number) => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => {
      const el = ref.current;
      if (el) el.style.transform = `translate(${x}px, ${y}px)`;
    });
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduced) return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const dx = (e.clientX - (rect.left + rect.width / 2)) * strength;
    const dy = (e.clientY - (rect.top + rect.height / 2)) * strength;
    apply(dx, dy);
  };

  const onPointerLeave = () => {
    if (reduced) return;
    apply(0, 0);
  };

  return (
    <div
      ref={ref}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      style={{
        display: "inline-block",
        transition: reduced ? undefined : "transform 220ms cubic-bezier(0.22, 1, 0.36, 1)",
        willChange: reduced ? undefined : "transform",
      }}
    >
      {children}
    </div>
  );
}

export default Magnetic;
