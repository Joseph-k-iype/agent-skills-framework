import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/shared/api/client", () => ({
  http: { get: vi.fn() },
  unwrap: (p: Promise<{ data: { data: unknown } }>) => p.then((r) => r.data.data),
}));

import { http } from "@/shared/api/client";
import { useInfiniteMarketplace, useTopRanked } from "../publicMarketplaceApi";

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const listing = (id: string) => ({
  id,
  title: `T${id}`,
  featured: false,
  version: "1",
  tags: [],
  downloads: 0,
});

afterEach(() => vi.clearAllMocks());

describe("useInfiniteMarketplace", () => {
  it("requests limit=pageSize & offset=0 on the first page and exposes hasNextPage when full", async () => {
    const page = Array.from({ length: 3 }, (_, i) => listing(`a${i}`));
    vi.mocked(http.get).mockResolvedValue({ data: { data: page } });

    const { result } = renderHook(() => useInfiniteMarketplace({ sort: "uses" }, 3), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // First call used offset 0 and limit 3.
    expect(http.get).toHaveBeenCalledWith(
      "/public/marketplace",
      expect.objectContaining({ params: expect.objectContaining({ limit: 3, offset: 0, sort: "uses" }) }),
    );
    // A full page (=== pageSize) means there is a next page.
    expect(result.current.hasNextPage).toBe(true);
  });

  it("stops paginating when a short page comes back", async () => {
    vi.mocked(http.get).mockResolvedValue({ data: { data: [listing("only")] } });
    const { result } = renderHook(() => useInfiniteMarketplace({ sort: "uses" }, 3), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.hasNextPage).toBe(false);
  });
});

describe("useTopRanked", () => {
  it("requests sort=uses with the given limit and no filters", async () => {
    const top = [listing("top1"), listing("top2")];
    vi.mocked(http.get).mockResolvedValue({ data: { data: top } });
    const { result } = renderHook(() => useTopRanked(8), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith(
      "/public/marketplace",
      { params: { sort: "uses", limit: 8, offset: 0 } },
    );
    expect(result.current.data).toHaveLength(2);
  });
});
