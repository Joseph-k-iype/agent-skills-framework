import { useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface TaxonomyTerm {
  key: string;
  label: string;
  description?: string | null;
  status: string;
  parent_key?: string | null;
}

export interface TaxonomyList {
  terms: TaxonomyTerm[];
}

export function useTaxonomyTerms(kind: "capabilities" | "sources") {
  return useQuery({
    queryKey: ["taxonomy", kind],
    queryFn: () => unwrap<TaxonomyList>(http.get(`/taxonomy/${kind}`)),
    staleTime: 5 * 60 * 1000, // taxonomy lists change rarely
  });
}
