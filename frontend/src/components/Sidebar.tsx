import type { Document } from "../types";
import SearchInput from "./SearchInput";
import SessionList from "./SessionList";
import DocumentMenu from "./DocumentMenu";

interface SidebarProps {
  documents: Document[];
  selectedDoc: Document | null;
  onSelectDoc: (doc: Document | null) => void;
  onNewChat: () => void;
  onUploadClick: () => void;
  isOpen: boolean;
  onClose: () => void;
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onRenameDoc: (doc: Document) => void;
  onDeleteDoc: (doc: Document) => void;
  onViewVersions: (doc: Document) => void;
}

export default function Sidebar({
  documents,
  selectedDoc,
  onSelectDoc,
  onNewChat,
  onUploadClick,
  isOpen,
  onClose,
  activeSessionId,
  onSelectSession,
  onRenameDoc,
  onDeleteDoc,
  onViewVersions,
}: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          data-testid="mobile-overlay"
          className="fixed inset-0 bg-black/30 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative z-50 lg:z-auto
          w-sidebar h-full bg-surface border-r border-outline
          flex flex-col shrink-0
          transition-transform duration-300 ease-material
          ${isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Header: New Chat */}
        <div className="p-3 border-b border-outline">
          <button
            onClick={() => { onNewChat(); onClose(); }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-material-full border border-outline hover:bg-surface-container hover:shadow-material-btn transition-all duration-200"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-google-blue">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span className="text-[14px] text-onsurface font-medium">Cuộc trò chuyện mới</span>
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pt-3">
          <SearchInput onSelectDoc={(doc) => { onSelectDoc(doc); onClose(); }} />
        </div>

        {/* Documents section */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="px-3 py-2">
            <p className="text-[11px] text-onsurface-muted font-medium uppercase tracking-wider">Tài liệu</p>
          </div>

          {/* Upload button */}
          <button
            onClick={onUploadClick}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-material hover:bg-surface-container transition-colors duration-200 text-left"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-google-blue">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="text-[13px] text-onsurface-variant">Tải lên tài liệu</span>
          </button>

          {/* Document list */}
          {documents.length === 0 ? (
            <p className="px-3 py-4 text-[12px] text-onsurface-muted text-center">
              Chưa có tài liệu. Tải lên để bắt đầu.
            </p>
          ) : (
            <div className="space-y-0.5">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => { onSelectDoc(doc); onClose(); }}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2 rounded-material text-left transition-colors duration-200
                    ${selectedDoc?.id === doc.id
                      ? "bg-google-blue/10 text-google-blue"
                      : "hover:bg-surface-container text-onsurface"
                    }
                  `}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={selectedDoc?.id === doc.id ? "text-google-blue" : "text-onsurface-muted"}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] truncate font-medium">
                      {doc.title || doc.fileName}
                    </p>
                    <p className="text-[11px] text-onsurface-muted truncate">
                      {doc.documentNumber ? `Số: ${doc.documentNumber}` : doc.fileType} &bull; {doc.chunkCount} chunks
                    </p>
                  </div>
                  <DocumentMenu
                    document={doc}
                    onRename={() => onRenameDoc(doc)}
                    onDelete={() => onDeleteDoc(doc)}
                    onViewHistory={() => onViewVersions(doc)}
                  />
                </button>
              ))}
            </div>
          )}
        </div>
        {/* Sessions */}
        <SessionList activeSessionId={activeSessionId} onSelectSession={(id) => { onSelectSession(id); onClose(); }} />

        {/* Footer */}
        <div className="p-3 border-t border-outline">
          <div className="px-2 text-[11px] text-onsurface-muted text-center leading-4">
            Smart Doc &bull; Enterprise CRAG
          </div>
        </div>
      </aside>
    </>
  );
}
