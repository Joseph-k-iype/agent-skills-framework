import { useEffect, useState, type ReactNode } from "react";
import { useInView } from "./useInView";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Reveals `children` when they scroll into view: opacity 0→1 and
 * translateY(y)→0 over ~420ms, after `delay` ms (used for card stagger).
 * Reduced motion → visible immediately, no transform.
 */
export function Reveal({
  children,
  delay = 0,
  y = 12,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
}) {
  const reduced = usePrefersReducedMotion();
  const [ref, inView] = useInView<HTMLDivElement>();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!inView) return;
    if (delay <= 0) {
      setShown(true);
      return;
    }
    const t = setTimeout(() => setShown(true), delay);
    return () => clearTimeout(t);
  }, [inView, delay]);

  const visible = reduced || shown;

  return (
    <div
      ref={ref}
      style={{
        opacity: reduced ? 1 : visible ? 1 : 0,
        transform: reduced ? "none" : visible ? "translateY(0)" : `translateY(${y}px)`,
        transition: reduced ? "none" : "opacity 420ms ease, transform 420ms ease",
        willChange: reduced ? undefined : "opacity, transform",
      }}
    >
      {children}
    </div>
  );
}

export default Reveal;
