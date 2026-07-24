import { useQuery } from "@tanstack/react-query";
import { useAuth, API_BASE_URL } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

interface Document {
  id: number;
  fileName: string;
  status: string;
}

interface AuditLog {
  id: number;
  action: string;
  createdAt: string;
}

export default function DashboardPage() {
  const { token, isAdmin } = useAuth();
  const navigate = useNavigate();

  const { data: documents = [] } = useQuery<Document[]>({
    queryKey: ["documents", token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch documents");
      return res.json();
    },
    enabled: !!token,
  });

  const { data: auditLogs = [] } = useQuery<AuditLog[]>({
    queryKey: ["auditLogs", token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/audit`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch audit logs");
      return res.json();
    },
    enabled: !!token && isAdmin,
  });

  const { data: metrics } = useQuery({
    queryKey: ["metrics", token],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE_URL.replace("/api", "")}/system/metrics`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!token,
  });

  const readyDocs = documents.filter((d) => d.status === "READY").length;
  const processingDocs = documents.filter(
    (d) => d.status === "PROCESSING",
  ).length;
  const failedDocs = documents.filter((d) => d.status === "FAILED").length;

  const recentActivity = auditLogs.slice(0, 5);

  const stats = [
    {
      label: "Total Documents",
      value: String(documents.length),
      hint: `${readyDocs} ready, ${processingDocs} processing`,
    },
    {
      label: "Failed Documents",
      value: String(failedDocs),
      hint: failedDocs > 0 ? "Needs attention" : "All healthy",
    },
    {
      label: "Avg LLM Latency",
      value: metrics?.average_latency_ms
        ? `${metrics.average_latency_ms}ms`
        : "--",
      hint: metrics?.p95_latency_ms
        ? `p95: ${metrics.p95_latency_ms}ms`
        : "No data yet",
    },
    {
      label: "Total Requests",
      value: metrics?.total_requests ? String(metrics.total_requests) : "--",
      hint: metrics?.error_rate
        ? `${(metrics.error_rate * 100).toFixed(1)}% errors`
        : "No data yet",
    },
  ];

  const quickLinks = [
    {
      title: "Classic Chat",
      desc: "Chat with your documents",
      href: "/classic",
    },
    { title: "Agent Chat", desc: "Multi-agent analysis", href: "/agent" },
    {
      title: "Data Sources",
      desc: "Manage connectors and sync",
      href: "/datasources",
    },
    { title: "8D Cases", desc: "Review incident workflows", href: "/eightd" },
    {
      title: "Knowledge Base",
      desc: "Browse all documents",
      href: "/knowledge",
    },
    {
      title: "Audit Logs",
      desc: "Security activity",
      href: "/audit",
      adminOnly: true,
    },
  ];

  const visibleLinks = quickLinks.filter((l) => !l.adminOnly || isAdmin);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Dashboard</h2>
        <p className="text-sm text-gray-500">
          Overview of the enterprise knowledge and operations workspace.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
          >
            <div className="text-sm text-gray-500">{stat.label}</div>
            <div className="mt-2 text-2xl font-semibold text-gray-800">
              {stat.value}
            </div>
            <div
              className={`mt-1 text-xs ${stat.hint.includes("error") || stat.hint.includes("attention") ? "text-rose-600" : "text-emerald-600"}`}
            >
              {stat.hint}
            </div>
          </div>
        ))}
      </div>

      {/* Quick access */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold text-gray-800">Quick access</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          {visibleLinks.map((link) => (
            <button
              key={link.title}
              type="button"
              className="rounded-xl border border-gray-200 p-3 text-left transition hover:border-indigo-300 hover:bg-indigo-50"
              onClick={() => navigate(link.href)}
            >
              <div className="font-medium text-gray-800">{link.title}</div>
              <div className="mt-1 text-sm text-gray-500">{link.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      {isAdmin && recentActivity.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="font-semibold text-gray-800">Recent activity</h3>
          <div className="mt-3 space-y-2">
            {recentActivity.map((log) => (
              <div
                key={log.id}
                className="flex items-center justify-between text-sm border-b border-gray-100 pb-2"
              >
                <span className="font-medium text-gray-700">{log.action}</span>
                <span className="text-xs text-gray-400">
                  {new Date(log.createdAt).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
