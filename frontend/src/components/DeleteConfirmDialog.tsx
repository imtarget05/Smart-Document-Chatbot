interface DeleteConfirmDialogProps {
  open: boolean;
  documentName: string;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
}

export default function DeleteConfirmDialog({
  open,
  documentName,
  onClose,
  onConfirm,
  loading = false,
}: DeleteConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-material-2xl shadow-material-3 p-6 max-w-sm w-[90%] animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-material-full bg-red-50 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d93025" strokeWidth="2" strokeLinecap="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </div>
          <h3 className="text-[16px] font-medium text-onsurface">Xóa tài liệu?</h3>
        </div>

        <p className="text-[13px] text-onsurface-muted mb-5">
          Bạn có chắc muốn xóa &quot;<span className="font-medium text-onsurface">{documentName}</span>&quot;?
          Hành động này không thể hoàn tác.
        </p>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-[13px] text-onsurface-variant hover:bg-surface-container rounded-material-full transition disabled:opacity-50"
          >
            Hủy
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-[13px] text-white bg-google-red hover:bg-red-700 rounded-material-full transition shadow-material-btn disabled:opacity-50 disabled:shadow-none"
          >
            {loading ? "Đang xóa..." : "Xóa"}
          </button>
        </div>
      </div>
    </div>
  );
}
