import { Link } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { NumberTicker } from "@/features/shared/fancy/NumberTicker";
import { Reveal } from "@/features/shared/fancy/Reveal";
import { Shimmer } from "@/features/shared/fancy/Shimmer";
import { categoryAccentFor } from "@/features/marketplace/theme";
import { RADIUS, storefrontType, swatchStyle } from "@/features/marketplace/storefront";
import { useTopRanked } from "../api/publicMarketplaceApi";

/**
 * Fixed "Top ranked" leaderboard — top 8 skills by cumulative uses. A stable
 * global "best of": rank numeral, category swatch, title, a proportional mini
 * bar (share of the #1 skill's uses), and an animated use count. Loading → 8
 * shimmer rows; empty → renders nothing (the page suppresses the board).
 */
export function TopRankedBoard() {
  const { data, isLoading } = useTopRanked(8);

  if (isLoading) {
    return (
      <section style={{ marginBottom: 40 }}>
        <BoardHeading />
        <div style={{ display: "grid", gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Shimmer key={i} height={44} radius={RADIUS} />
          ))}
        </div>
      </section>
    );
  }

  const rows = data ?? [];
  if (rows.length === 0) return null;

  const top = Math.max(1, rows[0].downloads);

  return (
    <section style={{ marginBottom: 40 }}>
      <BoardHeading />
      <div style={{ display: "grid", gap: 8 }}>
        {rows.map((listing, i) => {
          const category = listing.category ?? listing.type ?? "skill";
          const share = Math.max(0.04, listing.downloads / top);
          return (
            <Reveal key={listing.id} delay={i * 45}>
              <Link
                to={`/marketplace/${listing.id}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 12px",
                  background: tokens.color.surface,
                  border: `1px solid ${tokens.color.line}`,
                  borderRadius: RADIUS,
                  textDecoration: "none",
                }}
              >
                <span
                  style={{
                    ...storefrontType.monoSmall,
                    color: tokens.color.ink3,
                    width: 20,
                    flexShrink: 0,
                  }}
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span aria-hidden style={swatchStyle(categoryAccentFor(category))} />
                <span
                  style={{
                    ...storefrontType.title,
                    fontSize: 14,
                    flex: "0 0 auto",
                    maxWidth: 260,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {listing.title}
                </span>
                {/* Proportional mini bar — share of #1 uses. */}
                <span
                  aria-hidden
                  style={{ flex: 1, height: 4, background: tokens.color.line, borderRadius: 2 }}
                >
                  <span
                    style={{
                      display: "block",
                      height: "100%",
                      width: `${Math.round(share * 100)}%`,
                      background: categoryAccentFor(category),
                      borderRadius: 2,
                    }}
                  />
                </span>
                <NumberTicker
                  value={listing.downloads}
                  style={{ ...storefrontType.mono, color: tokens.color.ink2, flexShrink: 0 }}
                />
              </Link>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

function BoardHeading() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 10,
        padding: "0 0 12px",
        marginBottom: 12,
        borderBottom: `1px solid ${tokens.color.line}`,
      }}
    >
      <span style={storefrontType.eyebrow}>TOP RANKED</span>
      <span style={{ ...storefrontType.monoSmall }}>by uses</span>
    </div>
  );
}

export default TopRankedBoard;
