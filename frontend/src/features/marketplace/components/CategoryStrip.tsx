import { tokens } from "@/app/theme/tokens";
import type { Category } from "@/features/marketplace/api/publicMarketplaceApi";
import { tint } from "@/features/marketplace/theme";

interface CategoryStripProps {
  categories: Category[];
  active: string | undefined;
  onSelect: (category: string | undefined) => void;
}

/** Horizontal-scroll pill row: "◆ All" + one pill per category, red-tinted when active. */
export function CategoryStrip({ categories, active, onSelect }: CategoryStripProps) {
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        overflowX: "auto",
        paddingBottom: 2,
      }}
    >
      <Pill label="◆ All" isActive={!active} onClick={() => onSelect(undefined)} />
      {categories.map((c) => (
        <Pill
          key={c.category}
          label={`${c.category} · ${c.count}`}
          isActive={active === c.category}
          onClick={() => onSelect(active === c.category ? undefined : c.category)}
        />
      ))}
    </div>
  );
}

function Pill({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        cursor: "pointer",
        whiteSpace: "nowrap",
        font: `${isActive ? 600 : 500} 11px ${tokens.font.sans}`,
        color: isActive ? tokens.color.accent : tokens.color.ink2,
        background: isActive ? tint(tokens.color.accent, 0.08) : tokens.color.canvas,
        border: `1px solid ${isActive ? tint(tokens.color.accent, 0.3) : tokens.color.line}`,
        padding: "6px 12px",
        borderRadius: 999,
        textTransform: "capitalize",
        flexShrink: 0,
      }}
    >
      {label}
    </button>
  );
}
