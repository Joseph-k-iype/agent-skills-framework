import { useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface Listing {
  id: string;
  source_workspace_id: string;
  source_path: string;
  title: string;
  summary?: string | null;
  type?: string | null;
  runtime?: string | null;
  version: string;
  tags: string[];
  downloads: number; // "uses" counter
  author_id?: string | null;
  created_at?: string | null;
}

export interface ListingDetail extends Listing {
  content: string;
}

export type SortKey = "uses" | "recent" | "newest";

export function useMarketplace(q: string, type: string | undefined, sort: SortKey) {
  return useQuery({
    queryKey: ["marketplace", q, type ?? "", sort],
    queryFn: () =>
      unwrap<Listing[]>(
        http.get(`/marketplace`, {
          params: { q: q || undefined, type: type || undefined, sort },
        }),
      ),
  });
}

export function useListing(id: string | undefined) {
  return useQuery({
    queryKey: ["marketplace-listing", id],
    queryFn: () => unwrap<ListingDetail>(http.get(`/marketplace/${id}`)),
    enabled: !!id,
  });
}
