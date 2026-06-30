import { useState } from "react";
import { Link } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import type { PublicListing } from "@/features/marketplace/api/publicMarketplaceApi";
import { accentFor } from "@/features/marketplace/theme";
import { RADIUS, cardBorder, storefrontType, swatchStyle } from "@/features/marketplace/storefront";

function shortAuthor(authorId?: string | null): string {
  if (!authorId) return "anonymous";
  return authorId.length > 10 ? authorId.slice(0, 8) : authorId;
}

function formatDownloads(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`;
  return String(n);
}

/**
 * Marketplace listing card — Swiss storefront spec: hairline border, 4px
 * radius, no shadow. Tesla Red is reserved for the featured tick only; the
 * category swatch is the sole other color source. All data (category code,
 * sha, downloads) renders in monospace.
 */
export function SkillCard({ listing }: { listing: PublicListing }) {
  const [hovered, setHovered] = useState(false);
  const category = listing.category ?? listing.type ?? "skill";
  const shortSha = listing.latest_sha ? listing.latest_sha.slice(0, 7) : null;

  return (
    <Link
      to={`/marketplace/${listing.id}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      style={{
        display: "block",
        background: tokens.color.surface,
        border: cardBorder(hovered),
        borderRadius: RADIUS,
        padding: 16,
        textDecoration: "none",
        transition: "border-color 120ms ease",
      }}
    >
      {/* Top row: category swatch + mono label, featured tick (the only red), mono type code */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <span aria-hidden style={swatchStyle(accentFor(category))} />
        <span style={storefrontType.eyebrow}>{category}</span>
        {listing.featured && (
          <span
            aria-label="Featured"
            title="Featured"
            style={{
              marginLeft: "auto",
              color: tokens.color.accent,
              fontSize: 13,
              lineHeight: 1,
            }}
          >
            &#10003;
          </span>
        )}
        <span
          style={{
            ...storefrontType.monoSmall,
            marginLeft: listing.featured ? 6 : "auto",
            textTransform: "uppercase",
          }}
        >
          {listing.type}
        </span>
      </div>

      {/* Title */}
      <div style={{ ...storefrontType.title, marginBottom: 6 }}>{listing.title}</div>

      {/* Summary — variable length drives masonry height */}
      <div style={{ ...storefrontType.body, marginBottom: 12 }}>
        {listing.summary || "No description provided."}
      </div>

      {/* Tags — hairline mono chips, max 3 */}
      {listing.tags.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
          {listing.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              style={{
                ...storefrontType.monoSmall,
                border: `1px solid ${tokens.color.line}`,
                borderRadius: RADIUS,
                padding: "2px 6px",
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Hairline divider + footer: author, sha, downloads */}
      <div
        style={{
          borderTop: `1px solid ${tokens.color.line}`,
          paddingTop: 10,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span
          aria-hidden
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 16,
            height: 16,
            background: tokens.color.line,
            color: tokens.color.ink2,
            borderRadius: 2,
            font: `600 9px ${tokens.font.mono}`,
            flexShrink: 0,
          }}
        >
          {shortAuthor(listing.author_id).charAt(0).toUpperCase()}
        </span>
        <span style={{ ...storefrontType.monoSmall, color: tokens.color.ink3 }}>
          @{shortAuthor(listing.author_id)}
        </span>
        {shortSha && (
          <span style={{ ...storefrontType.monoSmall, marginLeft: "auto" }}>sha {shortSha}</span>
        )}
        <span style={{ ...storefrontType.monoSmall, marginLeft: shortSha ? 0 : "auto" }}>
          {formatDownloads(listing.downloads)}
        </span>
      </div>
    </Link>
  );
}
