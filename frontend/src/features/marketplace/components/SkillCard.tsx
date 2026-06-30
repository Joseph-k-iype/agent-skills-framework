import { Link } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import type { PublicListing } from "@/features/marketplace/api/publicMarketplaceApi";
import { tint } from "@/features/marketplace/theme";

/** Deterministic avatar-dot gradient from author id — purely decorative. */
function avatarGradient(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  const hue = hash % 360;
  return `linear-gradient(135deg, hsl(${hue}, 70%, 45%), hsl(${(hue + 35) % 360}, 80%, 65%))`;
}

function shortAuthor(authorId?: string | null): string {
  if (!authorId) return "anonymous";
  return authorId.length > 10 ? authorId.slice(0, 8) : authorId;
}

function formatDownloads(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`;
  return String(n);
}

/**
 * Marketplace listing card — matches the approved mockup:
 * featured/category pills, serif headline, clamped summary, tag chips,
 * author/rating/downloads footer, mono SHA badge + ink-black CTA.
 */
export function SkillCard({ listing }: { listing: PublicListing }) {
  const category = listing.category ?? listing.type ?? "skill";
  const shortSha = listing.latest_sha ? listing.latest_sha.slice(0, 7) : null;

  return (
    <div
      style={{
        background: tokens.color.surface,
        border: `1px solid ${tokens.color.line}`,
        borderRadius: tokens.radius,
        boxShadow: "0 8px 22px -18px rgba(0,0,0,.18)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: "15px 15px 13px", display: "flex", flexDirection: "column", flex: 1 }}>
        {/* Featured + category pills */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 11, flexWrap: "wrap" }}>
          {listing.featured && (
            <span
              style={{
                font: "600 9px " + tokens.font.sans,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: tokens.color.accent,
                background: tint(tokens.color.accent, 0.08),
                padding: "4px 7px",
                borderRadius: 999,
              }}
            >
              ★ Featured
            </span>
          )}
          <span
            style={{
              font: "600 10px " + tokens.font.sans,
              color: tokens.color.ink2,
              background: tokens.color.canvas,
              border: `1px solid ${tokens.color.line}`,
              padding: "4px 7px",
              borderRadius: 999,
              textTransform: "capitalize",
            }}
          >
            {category}
          </span>
        </div>

        {/* Headline */}
        <div
          style={{
            font: `600 16px/1.25 ui-serif, Georgia, "Times New Roman", serif`,
            color: tokens.color.ink,
            marginBottom: 5,
          }}
        >
          {listing.title}
        </div>

        {/* Summary, 2-line clamp */}
        <div
          style={{
            font: "400 12px/1.5 " + tokens.font.sans,
            color: tokens.color.ink2,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            minHeight: 36,
          }}
        >
          {listing.summary || "No description provided."}
        </div>

        {/* Tag chips (max 3) */}
        {listing.tags.length > 0 && (
          <div style={{ display: "flex", gap: 5, marginTop: 11, flexWrap: "wrap" }}>
            {listing.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                style={{
                  font: "500 10px " + tokens.font.sans,
                  color: tokens.color.ink3,
                  background: tokens.color.canvas,
                  padding: "3px 7px",
                  borderRadius: 4,
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Footer: author, rating placeholder, downloads */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 13,
            paddingTop: 11,
            borderTop: `1px solid ${tokens.color.line}`,
          }}
        >
          <span
            aria-hidden
            style={{
              width: 18,
              height: 18,
              borderRadius: "50%",
              background: avatarGradient(listing.author_id ?? listing.id),
              flexShrink: 0,
            }}
          />
          <span style={{ font: "500 11px " + tokens.font.sans, color: tokens.color.ink2 }}>
            @{shortAuthor(listing.author_id)}
          </span>
          <span
            style={{
              font: "600 11px " + tokens.font.sans,
              color: tokens.color.ink3,
              marginLeft: "auto",
            }}
          >
            ★ —
          </span>
          <span style={{ font: "400 11px " + tokens.font.sans, color: tokens.color.ink3 }}>
            {formatDownloads(listing.downloads)}
          </span>
        </div>

        {/* SHA badge + CTA */}
        <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8 }}>
          {shortSha && (
            <span
              style={{
                font: "500 9px " + tokens.font.mono,
                color: tokens.color.ink3,
                border: `1px solid ${tokens.color.line}`,
                background: tokens.color.canvas,
                padding: "3px 6px",
                borderRadius: 5,
                whiteSpace: "nowrap",
              }}
            >
              sha {shortSha}
            </span>
          )}
          <Link
            to={`/marketplace/${listing.id}`}
            style={{
              flex: 1,
              textAlign: "center",
              font: "600 11px " + tokens.font.sans,
              color: tokens.color.surface,
              background: tokens.color.ink,
              padding: "6px",
              borderRadius: 6,
              textDecoration: "none",
            }}
          >
            Use skill
          </Link>
        </div>
      </div>
    </div>
  );
}
