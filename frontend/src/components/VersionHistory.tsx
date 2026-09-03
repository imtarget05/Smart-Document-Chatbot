import { useDocumentVersions, type DocumentVersion } from "../hooks/useDocumentVersions";

interface VersionHistoryProps {
  documentId: number | null;
  documentName: string;
  onClose: () => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatBytes(bytes?: number): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export default function VersionHistory({ documentId, documentName, onClose }: VersionHistoryProps) {
  const { data: versions = [], isLoading } = useDocumentVersions(documentId);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="version-history">
      <div className="absolute inset-0 bg-black/40 animate-fade-in" onClick={onClose} />
      <aside className="relative w-full max-w-md h-full bg-surface shadow-material-4 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-outline">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-onsurface truncate">Lịch sử phiên bản</h2>
            <p className="text-xs text-onsurface-muted truncate">{documentName}</p>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-material-full hover:bg-surface-container text-onsurface-muted hover:text-onsurface transition flex items-center justify-center"
            aria-label="Đóng"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading && (
            <p className="text-sm text-onsurface-muted">Đang tải...</p>
          )}
          {!isLoading && versions.length === 0 && (
            <p className="text-sm text-onsurface-muted text-center py-8">
              Chưa có lịch sử phiên bản.
            </p>
          )}
          <div className="space-y-3">
            {versions.map((version, idx) => (
              <VersionItem key={version.versionNumber} version={version} isLatest={idx === 0} />
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}

function VersionItem({ version, isLatest }: { version: DocumentVersion; isLatest: boolean }) {
  return (
    <div className={`p-3 rounded-material-lg border ${isLatest ? "border-google-blue bg-google-blue/5" : "border-outline bg-surface"}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-onsurface">
          Phiên bản {version.versionNumber}
          {isLatest && (
            <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-material-full bg-google-blue text-white">
              Hiện tại
            </span>
          )}
        </p>
        {!isLatest && (
          <button className="text-[11px] text-google-blue font-medium hover:underline">
            Khôi phục
          </button>
        )}
      </div>
      <p className="text-[11px] text-onsurface-muted mt-1">{formatDate(version.createdAt)}</p>
      {version.fileSize && (
        <p className="text-[11px] text-onsurface-muted">{formatBytes(version.fileSize)}</p>
      )}
      {version.changeDescription && (
        <p className="text-[11px] text-onsurface mt-1">{version.changeDescription}</p>
      )}
    </div>
  );
}
