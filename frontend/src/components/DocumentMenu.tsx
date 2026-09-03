import { useState, useRef, useEffect } from "react";
import type { Document } from "../types";

interface DocumentMenuProps {
  document: Document;
  onRename: () => void;
  onDelete: () => void;
  onViewHistory: () => void;
}

export default function DocumentMenu({ onRename, onDelete, onViewHistory }: DocumentMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="w-7 h-7 rounded-material-full hover:bg-surface-container flex items-center justify-center text-onsurface-muted hover:text-onsurface transition"
        aria-label="Tùy chọn"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="5" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="19" r="2" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-surface border border-outline rounded-material-lg shadow-material-2 z-50 py-1 animate-fade-in">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              onRename();
            }}
            className="w-full text-left px-3 py-2 text-[13px] text-onsurface hover:bg-surface-container transition flex items-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            Đổi tên
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              onViewHistory();
            }}
            className="w-full text-left px-3 py-2 text-[13px] text-onsurface hover:bg-surface-container transition flex items-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            Lịch sử
          </button>
          <div className="h-[1px] bg-outline my-1" />
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              onDelete();
            }}
            className="w-full text-left px-3 py-2 text-[13px] text-google-red hover:bg-red-50 transition flex items-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            Xóa
          </button>
        </div>
      )}
    </div>
  );
}
