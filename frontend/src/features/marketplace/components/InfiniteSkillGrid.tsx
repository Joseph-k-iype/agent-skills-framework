import { useEffect } from "react";
import { tokens } from "@/app/theme/tokens";
import { Reveal } from "@/features/shared/fancy/Reveal";
import { Shimmer } from "@/features/shared/fancy/Shimmer";
import { Spotlight } from "@/features/shared/fancy/Spotlight";
import { useInView } from "@/features/shared/fancy/useInView";
import { GUTTER, RADIUS, storefrontType } from "@/features/marketplace/storefront";
import {
  useInfiniteMarketplace,
  type InfiniteParams,
  type PublicListing,
} from "../api/publicMarketplaceApi";
import { SkillCard } from "./SkillCard";

/**
 * The lazy-loading results grid. Flattens `useInfiniteMarketplace` pages into
 * the existing masonry wall (each card wrapped in Spotlight + Reveal, staggered
 * by index within its page), watches a bottom sentinel with `useInView`, and
 * calls `fetchNextPage` when the sentinel is visible and there is a next page.
 * Shows a shimmer row while fetching and an "end of results" hairline when done.
 */
export function InfiniteSkillGrid({
  params,
  masonryClass,
}: {
  params: InfiniteParams;
  masonryClass: string;
}) {
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteMarketplace(params);

  const [sentinelRef, sentinelInView] = useInView<HTMLDivElement>({ once: false, rootMargin: "300px" });

  useEffect(() => {
    if (sentinelInView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [sentinelInView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className={masonryClass}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
            <Shimmer height={180} radius={RADIUS} />
          </div>
        ))}
      </div>
    );
  }

  const pages = data?.pages ?? [];
  const flat: PublicListing[] = pages.flat();

  if (flat.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "60px 20px",
          color: tokens.color.ink3,
          font: `400 13px ${tokens.font.sans}`,
        }}
      >
        {params.q ? `No skills match "${params.q}".` : "No skills published yet."}
      </div>
    );
  }

  return (
    <>
      <div className={masonryClass}>
        {/* Stagger delay resets per page so later pages don't accumulate huge delays. */}
        {pages.map((page) =>
          page.map((listing, i) => (
            <div key={listing.id} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
              <Reveal delay={Math.min(i, 8) * 40}>
                <Spotlight>
                  <SkillCard listing={listing} />
                </Spotlight>
              </Reveal>
            </div>
          )),
        )}
      </div>

      {isFetchingNextPage && (
        <div className={masonryClass}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} style={{ breakInside: "avoid", marginBottom: GUTTER }}>
              <Shimmer height={160} radius={RADIUS} />
            </div>
          ))}
        </div>
      )}

      {/* Bottom sentinel — triggers the next page when scrolled near. */}
      <div ref={sentinelRef} aria-hidden style={{ height: 1 }} />

      {!hasNextPage && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            margin: "28px 0 0",
            color: tokens.color.ink3,
          }}
        >
          <span style={{ flex: 1, height: 1, background: tokens.color.line }} />
          <span style={{ ...storefrontType.monoSmall }}>end of results</span>
          <span style={{ flex: 1, height: 1, background: tokens.color.line }} />
        </div>
      )}
    </>
  );
}

export default InfiniteSkillGrid;
