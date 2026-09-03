import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export interface DocumentVersion {
  versionNumber: number;
  fileName: string;
  fileSize?: number;
  createdAt: string;
  createdBy?: string;
  changeDescription?: string;
}

interface VersionsResponse {
  versions: DocumentVersion[];
}

export function useDocumentVersions(documentId: number | null) {
  return useQuery<DocumentVersion[]>({
    queryKey: ["documentVersions", documentId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/documents/${documentId}/versions`, {
        headers: { ...(await csrfHeaders()) },
        credentials: "include",
      });
      if (!res.ok) return [];
      const data: VersionsResponse = await res.json();
      return data.versions ?? [];
    },
    enabled: documentId != null,
    staleTime: 60_000,
  });
}
