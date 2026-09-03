import { useState, useEffect } from "react";
import { useDocumentSearch } from "../hooks/useDocumentSearch";

interface SearchInputProps {
  onSelectDoc: (doc: { id: number; fileName: string; title?: string | null }) => void;
}

export default function SearchInput({ onSelectDoc }: SearchInputProps) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  const { data: results = [], isLoading } = useDocumentSearch(debounced);

  return (
    <div className="mb-3">
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 text-onsurface-muted"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tìm kiếm tài liệu..."
          className="w-full pl-9 pr-3 py-2.5 bg-surface-container border border-outline rounded-material text-[13px] text-onsurface placeholder:text-onsurface-muted focus:outline-none focus:border-google-blue focus:ring-1 focus:ring-google-blue"
          aria-label="Tìm kiếm tài liệu"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-onsurface-muted hover:text-onsurface"
            aria-label="Xóa tìm kiếm"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      {debounced && (
        <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
          {isLoading && (
            <p className="text-[12px] text-onsurface-muted px-2 py-1">Đang tìm...</p>
          )}
          {!isLoading && results.length === 0 && (
            <p className="text-[12px] text-onsurface-muted px-2 py-1">Không tìm thấy tài liệu</p>
          )}
          {results.map((doc) => (
            <button
              key={doc.id}
              onClick={() => {
                onSelectDoc({ id: doc.id, fileName: doc.fileName, title: doc.title });
                setQuery("");
              }}
              className="w-full text-left px-2 py-1.5 rounded-material hover:bg-surface-container transition"
            >
              <p className="text-[12px] text-onsurface truncate font-medium">
                📄 {doc.title || doc.fileName}
              </p>
              {doc.documentNumber && (
                <p className="text-[11px] text-onsurface-muted">
                  Số: {doc.documentNumber} • {doc.fileType} • {doc.chunkCount} chunks
                </p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
