import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export interface AuditLog {
  id: number;
  username: string;
  action: string;
  resourceType: string;
  resourceId: string;
  ipAddress: string;
  detail: string;
  createdAt: string;
}

interface AuditLogsResponse {
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
  logs: AuditLog[];
}

interface AuditLogsParams {
  page?: number;
  size?: number;
  username?: string;
  action?: string;
  from?: string;
}

export function useAuditLogs(params: AuditLogsParams = {}) {
  const { page = 0, size = 50, username, action, from } = params;

  return useQuery<AuditLogsResponse>({
    queryKey: ["auditLogs", page, size, username, action, from],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      searchParams.set("page", String(page));
      searchParams.set("size", String(size));
      if (username) searchParams.set("username", username);
      if (action) searchParams.set("action", action);
      if (from) searchParams.set("from", from);

      const res = await fetch(`${API_BASE_URL}/admin/audit-logs?${searchParams}`, {
        headers: { ...(await csrfHeaders()) },
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to fetch audit logs");
      return res.json();
    },
    placeholderData: (prev) => prev,
  });
}
