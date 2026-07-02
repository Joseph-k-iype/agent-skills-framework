import type { ReactNode } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import "./fancy.css";

/**
 * Seamless horizontal scroll: duplicates its track and animates the pair by
 * -50% via CSS. Reduced motion → a single static, horizontally scrollable row.
 */
export function Marquee({
  children,
  speed = 40,
  pauseOnHover = true,
}: {
  children: ReactNode;
  speed?: number;
  pauseOnHover?: boolean;
}) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return (
      <div style={{ overflowX: "auto", display: "flex", gap: 16, whiteSpace: "nowrap" }}>
        {children}
      </div>
    );
  }

  const trackStyle: React.CSSProperties = {
    display: "flex",
    gap: 16,
    width: "max-content",
    whiteSpace: "nowrap",
    animationDuration: `${speed}s`,
  };

  return (
    <div
      className={`fancy-marquee${pauseOnHover ? " fancy-marquee--paused" : ""}`}
      style={{ overflow: "hidden", display: "flex", width: "100%" }}
    >
      <div className="fancy-marquee-track" style={trackStyle}>
        <div style={{ display: "flex", gap: 16 }}>{children}</div>
        <div style={{ display: "flex", gap: 16 }} aria-hidden>
          {children}
        </div>
      </div>
    </div>
  );
}

export default Marquee;
