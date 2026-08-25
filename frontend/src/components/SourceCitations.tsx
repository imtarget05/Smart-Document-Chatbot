import { useState } from "react";
import type { SourceCitation } from "../types";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  OFFICIAL: "Văn bản chính thức",
  USER: "Tài liệu người dùng",
  FIXTURE: "Dữ liệu kiểm thử",
};

/** Builds "Điều N · Khoản M · Điểm K" from only the levels actually present. */
export function locationLabel(s: SourceCitation): string | null {
  const parts: string[] = [];
  if (s.article) parts.push(`Điều ${s.article}`);
  if (s.clause) parts.push(`Khoản ${s.clause}`);
  if (s.point) parts.push(`Điểm ${s.point}`);
  return parts.length > 0 ? parts.join(" · ") : null;
}

function CitationCard({
  source,
  index,
  onViewSource,
}: {
  source: SourceCitation;
  index: number;
  onViewSource?: (s: SourceCitation) => void;
}) {
  const title = source.documentTitle?.trim() || null;
  const location = locationLabel(source);
  const typeLabel = source.sourceType
    ? (SOURCE_TYPE_LABELS[source.sourceType] ?? null)
    : null;

  return (
    <div
      className="p-2.5 rounded-lg bg-gray-50 border border-gray-100 text-left"
      data-testid="citation-card"
      data-source-type={source.sourceType ?? "unknown"}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-gray-700 truncate" data-testid="citation-title">
            {title ?? "Không xác định tên văn bản"}
          </p>
          {source.documentNumber && (
            <p className="text-[11px] text-gray-500" data-testid="citation-number">
              Số: {source.documentNumber}
            </p>
          )}
          {location && (
            <p className="text-[11px] text-indigo-600 mt-0.5" data-testid="citation-location">
              {location}
            </p>
          )}
        </div>
        {onViewSource && source.documentId != null && (
          <button
            onClick={() => onViewSource(source)}
            className="shrink-0 text-[11px] px-2 py-1 rounded-md border border-gray-200 bg-white hover:bg-gray-100 text-gray-600 transition"
            data-testid={`view-source-${index}`}
          >
            Xem nguồn
          </button>
        )}
      </div>
      {source.content && (
        <p className="text-xs text-gray-500 leading-relaxed italic mt-1.5 line-clamp-3">
          "{source.content}"
        </p>
      )}
      {typeLabel && (
        <span
          className={`inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded ${
            source.sourceType === "OFFICIAL"
              ? "bg-green-50 text-green-700"
              : source.sourceType === "FIXTURE"
                ? "bg-purple-50 text-purple-700"
                : "bg-gray-100 text-gray-500"
          }`}
          data-testid="citation-source-type"
        >
          {typeLabel}
        </span>
      )}
    </div>
  );
}

/**
 * Structured citation list for an answer (Decision 14).
 *
 * - Renders backend-provided metadata only; missing fields are omitted,
 *   never invented.
 * - Falls back to legacy raw-chunk rendering when no structured sources exist.
 * - Preserves the source order returned by the backend.
 */
export default function SourceCitations({
  sources,
  sourceChunks,
  onViewSource,
}: {
  sources?: SourceCitation[] | null;
  sourceChunks?: string | null;
  onViewSource?: (s: SourceCitation) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  if (sources && sources.length > 0) {
    return (
      <div className="mt-3" data-testid="source-citations">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="cursor-pointer text-xs text-gray-500 hover:text-gray-700 transition flex items-center gap-1.5 select-none"
          data-testid="citations-toggle"
        >
          <span>📚</span> Nguồn hỗ trợ ({sources.length})
          <span className="text-[10px]">{expanded ? "▲" : "▼"}</span>
        </button>
        {expanded && (
          <div className="mt-2 space-y-2 max-h-64 overflow-y-auto pr-1">
            {sources.map((s, i) => (
              <CitationCard key={i} source={s} index={i} onViewSource={onViewSource} />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Legacy fallback: raw chunk text only (older persisted messages).
  if (sourceChunks) {
    return (
      <details className="mt-3 group">
        <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700 transition flex items-center gap-1.5 select-none">
          <span>📚</span> Sources
        </summary>
        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto pr-1">
          {sourceChunks.split("---").map((chunk, i) => {
            const match = chunk.trim().match(/^\[(.*?)\] (.*)$/s);
            const textContent = match ? match[2] : chunk;
            return (
              <div
                key={i}
                className="p-2.5 rounded-lg bg-gray-50 border border-gray-100 text-left"
              >
                <p className="text-xs text-gray-500 leading-relaxed italic">
                  "{textContent.trim()}"
                </p>
              </div>
            );
          })}
        </div>
      </details>
    );
  }

  return null;
}
