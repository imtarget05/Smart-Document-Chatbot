import { useState, useEffect } from "react";

interface RenameDialogProps {
  open: boolean;
  currentTitle?: string | null;
  currentNumber?: string | null;
  onClose: () => void;
  onSave: (data: { title: string; documentNumber: string }) => void;
  loading?: boolean;
}

export default function RenameDialog({
  open,
  currentTitle,
  currentNumber,
  onClose,
  onSave,
  loading = false,
}: RenameDialogProps) {
  const [title, setTitle] = useState("");
  const [number, setNumber] = useState("");

  useEffect(() => {
    if (open) {
      setTitle(currentTitle || "");
      setNumber(currentNumber || "");
    }
  }, [open, currentTitle, currentNumber]);

  if (!open) return null;

  const isValid = title.trim().length > 0 && title.trim().length <= 200;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-material-2xl shadow-material-3 p-6 max-w-sm w-[90%] animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-[16px] font-medium text-onsurface mb-4">Đổi tên tài liệu</h3>

        <div className="space-y-3">
          <div>
            <label className="text-[12px] text-onsurface-muted font-medium block mb-1">Tiêu đề</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Nhập tiêu đề..."
              className="w-full px-3 py-2.5 border border-outline rounded-material text-[14px] focus:outline-none focus:border-google-blue focus:ring-1 focus:ring-google-blue"
              maxLength={200}
              aria-label="Tiêu đề tài liệu"
            />
            <p className="text-[11px] text-onsurface-muted mt-1">{title.length}/200</p>
          </div>
          <div>
            <label className="text-[12px] text-onsurface-muted font-medium block mb-1">Số văn bản</label>
            <input
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="VD: HDLD-2024-001"
              className="w-full px-3 py-2.5 border border-outline rounded-material text-[14px] focus:outline-none focus:border-google-blue focus:ring-1 focus:ring-google-blue"
              aria-label="Số văn bản"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-[13px] text-onsurface-variant hover:bg-surface-container rounded-material-full transition disabled:opacity-50"
          >
            Hủy
          </button>
          <button
            disabled={!isValid || loading}
            onClick={() => onSave({ title: title.trim(), documentNumber: number.trim() })}
            className="px-4 py-2 text-[13px] text-white bg-google-blue hover:bg-google-blueDark rounded-material-full transition shadow-material-btn disabled:opacity-50 disabled:shadow-none"
          >
            {loading ? "Đang lưu..." : "Lưu"}
          </button>
        </div>
      </div>
    </div>
  );
}
