import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "../context/AuthContext";
import type { LegalDocumentDetail, SourceCitation } from "../types";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  OFFICIAL: "Văn bản chính thức",
  USER: "Tài liệu người dùng",
  FIXTURE: "Dữ liệu kiểm thử",
};

/**
 * Minimal document / article navigation view (Decision 14).
 *
 * Shows the legal metadata the backend actually provides plus the structured
 * evidence units (Điều/Khoản/Điểm). The cited article is highlighted via
 * anchor. Owner isolation is backend-enforced: another user's document
 * yields 404 and an honest error message here.
 */
export default function DocumentViewer({
  citation,
  token,
  onClose,
}: {
  citation: SourceCitation;
  token: string | null;
  onClose: () => void;
}) {
  const documentId = citation.documentId;
  const citedChunkId = citation.chunkId;

  const { data, isLoading, error } = useQuery<LegalDocumentDetail>({
    queryKey: ["legalDocument", documentId, token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/documents/${documentId}/legal-chunks`, {
        headers: { Authorization: `Bearer ${token ?? ""}` },
      });
      if (!res.ok) throw new Error("not_found");
      return res.json();
    },
    enabled: documentId != null && !!token,
  });

  const title = data?.title?.trim() || data?.fileName || "Không xác định tên văn bản";

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="document-viewer">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative w-full max-w-md h-full bg-white shadow-xl flex flex-col">
        <div className="flex items-start justify-between px-5 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-sm font-semibold text-gray-800" data-testid="viewer-title">
              {title}
            </h2>
            {data?.documentNumber && (
              <p className="text-xs text-gray-500">Số: {data.documentNumber}</p>
            )}
            {data && (
              <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                {SOURCE_TYPE_LABELS[data.sourceType] ?? data.sourceType}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition"
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>

        {isLoading && (
          <p className="px-5 py-6 text-sm text-gray-400">Đang tải tài liệu...</p>
        )}
        {error && (
          <p className="px-5 py-6 text-sm text-red-500" data-testid="viewer-error">
            Không thể mở tài liệu này.
          </p>
        )}

        {data && (
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {(data.issueDate || data.effectiveDate) && (
              <div className="text-[11px] text-gray-500">
                {data.issueDate && <p>Ngày ban hành: {data.issueDate}</p>}
                {data.effectiveDate && <p>Ngày hiệu lực: {data.effectiveDate}</p>}
              </div>
            )}
            {data.chunks.length === 0 ? (
              <p className="text-xs text-gray-400">
                Tài liệu này chưa có cấu trúc điều/khoản được nhận diện.
              </p>
            ) : (
              data.chunks.map((chunk) => {
                const label = [
                  chunk.article ? `Điều ${chunk.article}` : null,
                  chunk.clause ? `Khoản ${chunk.clause}` : null,
                  chunk.point ? `Điểm ${chunk.point}` : null,
                ]
                  .filter(Boolean)
                  .join(" · ");
                const isCited = citedChunkId != null && chunk.id === citedChunkId;
                return (
                  <div
                    key={chunk.id}
                    id={`legal-chunk-${chunk.id}`}
                    className={`p-3 rounded-lg border text-left ${
                      isCited
                        ? "border-indigo-300 bg-indigo-50"
                        : "border-gray-100 bg-gray-50"
                    }`}
                    data-cited={isCited || undefined}
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] font-medium text-indigo-600">
                        {label || "Nội dung chung"}
                      </p>
                      {isCited && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
                          Trích dẫn
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed mt-1 whitespace-pre-wrap">
                      {chunk.content}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
