import { useQuery } from "@tanstack/react-query";
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
