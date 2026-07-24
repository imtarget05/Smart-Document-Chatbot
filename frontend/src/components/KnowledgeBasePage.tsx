import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth, API_BASE_URL } from "../context/AuthContext";

interface Document {
  id: number;
  fileName: string;
  fileSize: number;
  fileType: string;
  chunkCount: number;
  status: "PROCESSING" | "READY" | "FAILED";
  summary?: string;
  createdAt: string;
}

export default function KnowledgeBasePage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const { data: documents = [], isLoading } = useQuery<Document[]>({
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

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to delete document");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setSelectedIds([]);
    },
  });

  const filteredDocs = documents.filter((d) => {
    const matchesSearch = d.fileName
      .toLowerCase()
      .includes(search.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredDocs.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredDocs.map((d) => d.id));
    }
  };

  const handleBulkDelete = () => {
    selectedIds.forEach((id) => deleteMutation.mutate(id));
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      READY: "bg-emerald-50 text-emerald-600 border-emerald-200",
      PROCESSING: "bg-amber-50 text-amber-600 border-amber-200",
      FAILED: "bg-rose-50 text-rose-600 border-rose-200",
    };
    return `rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase border ${colors[status] || "bg-gray-50 text-gray-600 border-gray-200"}`;
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">
            Knowledge Base
          </h2>
          <p className="text-sm text-gray-500">
            {documents.length} documents total
          </p>
        </div>
        {selectedIds.length > 0 && (
          <button
            onClick={handleBulkDelete}
            disabled={deleteMutation.isPending}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition"
          >
            {deleteMutation.isPending
              ? "Deleting..."
              : `Delete (${selectedIds.length})`}
          </button>
        )}
      </div>

      {/* Search & Filter */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search documents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:border-indigo-400"
        >
          <option value="ALL">All Status</option>
          <option value="READY">Ready</option>
          <option value="PROCESSING">Processing</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {/* Documents Grid */}
      {isLoading ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Loading documents…
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          {documents.length === 0
            ? "No documents uploaded yet. Upload a document to get started."
            : "No documents match your filters."}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              className={`rounded-2xl border p-4 shadow-sm transition ${
                selectedIds.includes(doc.id)
                  ? "border-indigo-400 bg-indigo-50"
                  : "border-gray-200 bg-white"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(doc.id)}
                    onChange={() => toggleSelect(doc.id)}
                    className="rounded border-gray-300"
                  />
                  <h3 className="font-semibold text-gray-800 text-sm">
                    {doc.fileName}
                  </h3>
                </div>
                <span className={statusBadge(doc.status)}>{doc.status}</span>
              </div>
              <div className="mt-2 space-y-1">
                <div className="text-xs text-gray-500">
                  <span className="font-medium">Size:</span>{" "}
                  {formatSize(doc.fileSize)} •{" "}
                  <span className="font-medium">Type:</span>{" "}
                  {doc.fileType?.toUpperCase()} •{" "}
                  <span className="font-medium">Chunks:</span> {doc.chunkCount}
                </div>
                {doc.summary && (
                  <p className="text-xs text-gray-500 line-clamp-2">
                    {doc.summary}
                  </p>
                )}
                <p className="text-[10px] text-gray-400">
                  Created: {new Date(doc.createdAt).toLocaleDateString()}
                </p>
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => deleteMutation.mutate(doc.id)}
                  className="text-[10px] font-bold text-rose-500 hover:text-rose-700 transition"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Select All */}
      {filteredDocs.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <input
            type="checkbox"
            checked={
              selectedIds.length === filteredDocs.length &&
              filteredDocs.length > 0
            }
            onChange={toggleSelectAll}
            className="rounded border-gray-300"
          />
          <span>Select all ({filteredDocs.length})</span>
        </div>
      )}
    </div>
  );
}
