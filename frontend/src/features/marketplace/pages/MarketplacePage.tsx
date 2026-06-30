import { SearchOutlined } from "@ant-design/icons";
import { Input, Skeleton } from "antd";
import { useEffect, useMemo, useState } from "react";
import { tokens } from "@/app/theme/tokens";
import { GUTTER, RADIUS, storefrontType } from "@/features/marketplace/storefront";
import { usePublicCategories, usePublicMarketplace, type SortKey } from "../api/publicMarketplaceApi";
import { SkillCard } from "../components/SkillCard";

const MASONRY_CLASS = "marketplace-masonry";

/**
 * Responsive masonry column count via inline media queries: 4 at ≥1200px,
 * 3 at ≥900px, 2 at ≥600px, 1 below. Scoped to MASONRY_CLASS so it doesn't
 * leak outside this page.
 */
function MasonryResponsiveStyle() {
  return (
    <style>{`
      .${MASONRY_CLASS} { column-count: 1; column-gap: ${GUTTER}px; }
      @media (min-width: 600px) { .${MASONRY_CLASS} { column-count: 2; } }
      @media (min-width: 900px) { .${MASONRY_CLASS} { column-count: 3; } }
      @media (min-width: 1200px) { .${MASONRY_CLASS} { column-count: 4; } }
    `}</style>
  );
}

export default function MarketplacePage() {
  const [category, setCategory] = useState<string | undefined>();
  const [sort, setSort] = useState<SortKey>("uses");
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");

  // Debounce the search input (~250ms) before it drives the query.
  useEffect(() => {
    const timer = setTimeout(() => setQ(qInput.trim()), 250);
    return () => clearTimeout(timer);
  }, [qInput]);

  const categories = usePublicCategories();
  const listings = usePublicMarketplace(q, undefined, category, sort);
  const data = useMemo(() => listings.data ?? [], [listings.data]);

  // Stable total across the whole catalog — does not fluctuate while
  // typing/filtering, unlike the filtered `data.length` below. Falls back
  // to the filtered count only until categories have loaded.
  const totalCount = useMemo(() => {
    const cats = categories.data;
    if (!cats || cats.length === 0) return data.length;
    return cats.reduce((sum, c) => sum + c.count, 0);
  }, [categories.data, data.length]);

  return (
    <div style={{ paddingBottom: 60 }}>
      <MasonryResponsiveStyle />
      {/* Hero: centered headline, count, search, category filters */}
      <div style={{ padding: "56px 0 40px", textAlign: "center" }}>
        <h1
          style={{
            margin: 0,
            font: `600 40px/1.15 ${tokens.font.sans}`,
            letterSpacing: "-0.02em",
            color: tokens.color.ink,
          }}
        >
          Find a data skill
        </h1>
        <div
          style={{
            marginTop: 10,
            font: `500 12px/1.4 ${tokens.font.mono}`,
            color: tokens.color.ink3,
          }}
        >
          {totalCount} skills · content-addressed
        </div>

        <div
          style={{
            margin: "28px auto 0",
            maxWidth: 560,
          }}
        >
          <Input
            allowClear
            size="large"
            prefix={<SearchOutlined style={{ color: tokens.color.ink3 }} aria-hidden />}
            placeholder="Search skills…"
            aria-label="Search skills"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            style={{
              borderRadius: RADIUS,
              border: `1px solid ${tokens.color.line}`,
              boxShadow: "none",
            }}
          />
        </div>

        {/* Category filters — the active one carries the only red marker. */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            flexWrap: "wrap",
            gap: 18,
            marginTop: 24,
          }}
        >
          <CategoryFilter label="All" isActive={!category} onClick={() => setCategory(undefined)} />
          {(categories.data ?? []).map((c) => (
            <CategoryFilter
              key={c.category}
              label={c.category}
              isActive={category === c.category}
              onClick={() => setCategory(category === c.category ? undefined : c.category)}
            />
          ))}
        </div>
      </div>

      {/* Section header: eyebrow + count, sort toggle */}
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          padding: "0 0 16px",
          borderBottom: `1px solid ${tokens.color.line}`,
          marginBottom: GUTTER,
        }}
      >
        <span style={storefrontType.eyebrow}>EXPLORE · {data.length}</span>
        <button
          type="button"
          onClick={() => setSort(sort === "uses" ? "recent" : "uses")}
          style={{
            marginLeft: "auto",
            cursor: "pointer",
            background: "none",
            border: "none",
            padding: 0,
            font: `500 12px ${tokens.font.sans}`,
            color: tokens.color.ink2,
          }}
        >
          {sort === "uses" ? "Trending" : "Newest"}
        </button>
      </div>

      {/* Masonry wall */}
      {listings.isLoading ? (
        <div className={MASONRY_CLASS}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              style={{
                breakInside: "avoid",
                marginBottom: GUTTER,
                background: tokens.color.surface,
                border: `1px solid ${tokens.color.line}`,
                borderRadius: RADIUS,
                padding: 16,
              }}
            >
              <Skeleton active paragraph={{ rows: 4 }} />
            </div>
          ))}
        </div>
      ) : data.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: tokens.color.ink3,
            font: `400 13px ${tokens.font.sans}`,
          }}
        >
          {q ? `No skills match "${q}".` : "No skills published yet."}
        </div>
      ) : (
        <div className={MASONRY_CLASS}>
          {data.map((listing) => (
            <div key={listing.id} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
              <SkillCard listing={listing} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryFilter({
  label,
  isActive,
  onClick,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        cursor: "pointer",
        background: "none",
        border: "none",
        padding: "2px 0",
        font: `${isActive ? 600 : 400} 13px ${tokens.font.sans}`,
        color: isActive ? tokens.color.ink : tokens.color.ink2,
        textTransform: "capitalize",
        position: "relative",
      }}
    >
      {label}
      {isActive && (
        <span
          aria-hidden
          style={{
            display: "block",
            position: "absolute",
            left: 0,
            right: 0,
            bottom: -4,
            height: 2,
            background: tokens.color.accent,
            borderRadius: 1,
          }}
        />
      )}
    </button>
  );
}
