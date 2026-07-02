import { tokens } from "@/app/theme/tokens";
import { Marquee } from "@/features/shared/fancy/Marquee";
import { RADIUS, storefrontType } from "@/features/marketplace/storefront";
import { categoryAccentFor } from "@/features/marketplace/theme";
import { usePublicCategories } from "../api/publicMarketplaceApi";

/**
 * A trending ribbon of category chips (top categories by count) that scrolls
 * seamlessly under the hero. Clicking a chip sets the category filter via
 * `onPick`. Renders nothing until categories load / when there are none.
 */
export function TrendingMarquee({ onPick }: { onPick: (category: string) => void }) {
  const { data } = usePublicCategories();
  const cats = (data ?? []).slice(0, 12);
  if (cats.length === 0) return null;

  return (
    <div style={{ marginBottom: 32 }}>
      <Marquee speed={40} pauseOnHover>
        {cats.map((c) => (
          <button
            key={c.category}
            type="button"
            onClick={() => onPick(c.category)}
            style={{
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: tokens.color.surface,
              border: `1px solid ${tokens.color.line}`,
              borderRadius: RADIUS,
              padding: "4px 10px",
              font: `500 12px ${tokens.font.sans}`,
              color: tokens.color.ink2,
              whiteSpace: "nowrap",
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: 1,
                background: categoryAccentFor(c.category),
              }}
            />
            <span style={{ textTransform: "capitalize" }}>{c.category}</span>
            <span style={{ ...storefrontType.monoSmall }}>{c.count}</span>
          </button>
        ))}
      </Marquee>
    </div>
  );
}

export default TrendingMarquee;
