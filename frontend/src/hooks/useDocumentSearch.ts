import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export interface SearchResult {
  id: number;
  fileName: string;
  title?: string | null;
  documentNumber?: string | null;
  fileType: string;
  chunkCount: number;
  relevanceScore?: number;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
}

export function useDocumentSearch(query: string) {
  return useQuery<SearchResult[]>({
    queryKey: ["documents", "search", query],
    queryFn: async () => {
      if (!query.trim()) return [];
      const res = await fetch(
        `${API_BASE_URL}/documents/search?q=${encodeURIComponent(query)}&limit=20`,
        { headers: { ...(await csrfHeaders()) }, credentials: "include" }
      );
      if (!res.ok) return [];
      const data: SearchResponse = await res.json();
      return data.results ?? [];
    },
    enabled: query.trim().length > 0,
    staleTime: 30_000,
  });
}
