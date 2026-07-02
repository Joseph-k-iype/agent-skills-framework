import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface PublicListing {
  id: string;
  title: string;
  summary?: string | null;
  type?: string | null;
  category?: string | null;
  featured: boolean;
  runtime?: string | null;
  version: string;
  latest_sha?: string | null;
  latest_version?: number | null;
  tags: string[];
  downloads: number;
  author_id?: string | null;
  created_at?: string | null;
}

export interface VersionRef {
  version: number;
  sha: string;
  changelog?: string | null;
  created_at?: string | null;
}

export interface PublicListingDetail extends PublicListing {
  content: string;
  versions: VersionRef[];
  clones: number;
}

export interface HistoryPoint {
  date: string;
  cumulative: number;
}

export interface Category {
  category: string;
  count: number;
}

export type SortKey = "uses" | "recent" | "newest";

export function usePublicMarketplace(
  q: string,
  type: string | undefined,
  category: string | undefined,
  sort: SortKey,
  capability?: string | undefined,
  source?: string | undefined,
) {
  return useQuery({
    queryKey: ["public-marketplace", q, type ?? "", category ?? "", sort, capability ?? "", source ?? ""],
    queryFn: () =>
      unwrap<PublicListing[]>(
        http.get(`/public/marketplace`, {
          params: {
            q: q || undefined,
            type: type || undefined,
            category: category || undefined,
            sort,
            capability: capability || undefined,
            source: source || undefined,
          },
        }),
      ),
  });
}

export function usePublicCategories() {
  return useQuery({
    queryKey: ["public-categories"],
    queryFn: () => unwrap<Category[]>(http.get(`/public/marketplace/categories`)),
  });
}

export function usePublicListing(id: string | undefined) {
  return useQuery({
    queryKey: ["public-listing", id],
    queryFn: () => unwrap<PublicListingDetail>(http.get(`/public/marketplace/${id}`)),
    enabled: !!id,
  });
}

export function useListingHistory(id: string | undefined, days = 90) {
  return useQuery({
    queryKey: ["public-listing-history", id, days],
    queryFn: () =>
      unwrap<HistoryPoint[]>(
        http.get(`/public/marketplace/${id}/history`, { params: { days } }),
      ),
    enabled: !!id,
  });
}

export interface InfiniteParams {
  q?: string;
  type?: string;
  category?: string;
  sort: SortKey;
  capability?: string;
  source?: string;
}

/**
 * Infinite/lazy grid over /public/marketplace. Sends `limit=pageSize` and
 * `offset=pageParam`; `hasMore` is inferred from `lastPage.length === pageSize`
 * (no total-count field). The query key includes every param so a filter,
 * search, or sort change refetches from page 0.
 */
export function useInfiniteMarketplace(params: InfiniteParams, pageSize = 24) {
  return useInfiniteQuery({
    queryKey: [
      "public-marketplace-infinite",
      params.q ?? "",
      params.type ?? "",
      params.category ?? "",
      params.sort,
      params.capability ?? "",
      params.source ?? "",
      pageSize,
    ],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap<PublicListing[]>(
        http.get(`/public/marketplace`, {
          params: {
            q: params.q || undefined,
            type: params.type || undefined,
            category: params.category || undefined,
            sort: params.sort,
            capability: params.capability || undefined,
            source: params.source || undefined,
            limit: pageSize,
            offset: pageParam,
          },
        }),
      ),
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length === pageSize ? allPages.length * pageSize : undefined,
  });
}

/**
 * The fixed "Top ranked" leaderboard: same route, `sort=uses`, no filters, its
 * own query key so grid filtering never disturbs it.
 */
export function useTopRanked(limit = 8) {
  return useQuery({
    queryKey: ["public-marketplace-top", limit],
    queryFn: () =>
      unwrap<PublicListing[]>(
        http.get(`/public/marketplace`, {
          params: { sort: "uses", limit, offset: 0 },
        }),
      ),
  });
}
