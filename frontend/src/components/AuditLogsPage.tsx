import { useQuery } from "@tanstack/react-query";

interface AuditLog {
  id: number;
  action: string;
  entityType: string;
  details: string;
  status: string;
  createdAt: string;
}

interface Props {
  token: string;
}

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8080/api";

export default function AuditLogsPage({ token }: Props) {
  const { data = [], isLoading } = useQuery<AuditLog[]>({
    queryKey: ["auditLogs", token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/audit`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load audit logs");
      return res.json();
    },
    enabled: !!token,
  });

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Audit Logs</h2>
        <p className="text-sm text-gray-500">
          Review important system activity and security events.
        </p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Loading audit logs…
        </div>
      ) : data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          No audit logs yet.
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((log) => (
            <div
              key={log.id}
              className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-gray-800">{log.action}</h3>
                  <p className="text-xs text-gray-500">{log.entityType}</p>
                </div>
                <span
                  className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${log.status === "FAILURE" ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"}`}
                >
                  {log.status}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-600">{log.details}</p>
              <p className="mt-2 text-xs text-gray-400">
                {new Date(log.createdAt).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
