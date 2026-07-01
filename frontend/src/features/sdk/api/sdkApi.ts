import { useQuery } from "@tanstack/react-query";
import { http, unwrap } from "@/shared/api/client";

export interface SkillListing {
  id: string;
  title: string;
  summary?: string | null;
  type?: string | null;
  runtime?: string | null;
  version: string;
  tags: string[];
  downloads: number;
}

/** Fetch the authed marketplace listing for skill-id selection in the snippet. */
export function useSkillListings() {
  return useQuery({
    queryKey: ["sdk-skill-listings"],
    queryFn: () =>
      unwrap<SkillListing[]>(http.get("/marketplace", { params: { sort: "recent" } })),
  });
}
