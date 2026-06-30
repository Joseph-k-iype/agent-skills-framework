import { Skeleton } from "antd";
import { useMemo, useState } from "react";
import { tokens } from "@/app/theme/tokens";
import { usePublicCategories, usePublicMarketplace, type SortKey } from "../api/publicMarketplaceApi";
import { CategoryStrip } from "../components/CategoryStrip";
import { SkillCard } from "../components/SkillCard";

export default function MarketplacePage() {
  const [category, setCategory] = useState<string | undefined>();
  const [sort, setSort] = useState<SortKey>("uses");

  const categories = usePublicCategories();
  const listings = usePublicMarketplace("", undefined, category, sort);
  const data = useMemo(() => listings.data ?? [], [listings.data]);

  return (
    <div style={{ paddingBottom: 60 }}>
      {/* Category strip */}
      <CategoryStrip categories={categories.data ?? []} active={category} onSelect={setCategory} />

      {/* Featured section header */}
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          padding: "20px 0 12px",
        }}
      >
        <div style={{ font: `600 16px ui-serif, Georgia, "Times New Roman", serif`, color: tokens.color.ink }}>
          Featured
        </div>
        <div style={{ font: "400 12px " + tokens.font.sans, color: tokens.color.ink3 }}>
          Curated this week
        </div>
        <button
          type="button"
          onClick={() => setSort(sort === "uses" ? "recent" : "uses")}
          style={{
            marginLeft: "auto",
            cursor: "pointer",
            background: "none",
            border: "none",
            padding: 0,
            font: "500 12px " + tokens.font.sans,
            color: tokens.color.accent,
          }}
        >
          {sort === "uses" ? "Trending →" : "Most used →"}
        </button>
      </div>

      {/* Grid */}
      {listings.isLoading ? (
        <div
          style={{
            display: "grid",
            gap: 14,
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          }}
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              style={{
                background: tokens.color.surface,
                border: `1px solid ${tokens.color.line}`,
                borderRadius: tokens.radius,
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
            font: "400 13px " + tokens.font.sans,
          }}
        >
          No skills match — publish a concept version to list it here.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gap: 14,
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          }}
        >
          {data.map((listing) => (
            <SkillCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}
    </div>
  );
}
