// frontend/src/features/shared/fancy/SaveFlash.tsx
import { CheckCircleFilled } from "@ant-design/icons";
import { tokens } from "@/app/theme/tokens";

/** Brief "Saved" confirmation badge; parent controls visibility timing. */
export function SaveFlash({ show }: { show: boolean }) {
  return (
    <span
      role="status"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        color: tokens.color.ok,
        fontSize: 13,
        opacity: show ? 1 : 0,
        transform: show ? "translateY(0)" : "translateY(4px)",
        transition: "opacity 240ms ease, transform 240ms ease",
        pointerEvents: "none",
      }}
    >
      {show && (
        <>
          <CheckCircleFilled /> Saved
        </>
      )}
    </span>
  );
}

export default SaveFlash;
