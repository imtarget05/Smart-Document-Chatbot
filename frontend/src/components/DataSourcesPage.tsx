import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

interface DataSource {
  id: number;
  name: string;
  type: string;
  connectionUrl: string;
  description: string;
  status: string;
}

interface Props {
  token: string;
}

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8080/api";

export default function DataSourcesPage({ token }: Props) {
  const [filter, setFilter] = useState("ALL");

  const { data = [], isLoading } = useQuery<DataSource[]>({
    queryKey: ["dataSources", token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/datasources`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        throw new Error("Failed to load data sources");
      }
      return res.json();
    },
    enabled: !!token,
  });

  const filtered = useMemo(() => {
    if (filter === "ALL") return data;
    return data.filter((item) => item.status === filter);
  }, [data, filter]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Data Sources</h2>
          <p className="text-sm text-gray-500">
            Connect and monitor ingestion sources for your knowledge base.
          </p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
        >
          <option value="ALL">All statuses</option>
          <option value="READY">Ready</option>
          <option value="SYNCING">Syncing</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Loading sources…
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          No sources available yet.
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((source) => (
            <div
              key={source.id}
              className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-gray-800">{source.name}</h3>
                  <p className="text-xs text-gray-500">{source.type}</p>
                </div>
                <span className="rounded-full bg-indigo-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-indigo-600">
                  {source.status}
                </span>
              </div>
              <p className="mt-3 text-sm text-gray-600">{source.description}</p>
              <p className="mt-3 truncate text-xs text-gray-400">
                {source.connectionUrl}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
