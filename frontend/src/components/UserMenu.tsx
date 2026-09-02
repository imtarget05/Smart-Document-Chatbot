import { useState, useRef, useEffect } from "react";

interface UserMenuProps {
  username?: string | null;
  role?: string | null;
  onLogout: () => void;
}

export default function UserMenu({ username, role, onLogout }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const initials = username ? username.slice(0, 2).toUpperCase() : "U";
  const roleLabel = role === "ROLE_ADMIN" || role === "ADMIN"
    ? "Quản trị viên"
    : role === "ROLE_ENGINEER" || role === "ENGINEER"
      ? "Kỹ sư"
      : role === "ROLE_VIEWER" || role === "VIEWER"
        ? "Người xem"
        : null;

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-9 h-9 rounded-material-full bg-google-blue text-white text-[13px] font-medium flex items-center justify-center hover:shadow-material-btn transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-google-blue/30"
        aria-label="Menu người dùng"
        aria-expanded={isOpen}
      >
        {initials}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-60 bg-surface border border-outline rounded-material-lg shadow-material-3 animate-fade-in z-50">
          {/* User info */}
          <div className="px-4 py-3 border-b border-outline">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-material-full bg-google-blue text-white text-[14px] font-medium flex items-center justify-center shrink-0">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="text-[14px] text-onsurface font-medium truncate">
                  {username || "User"}
                </p>
                {roleLabel && (
                  <p className="text-[12px] text-onsurface-muted">{roleLabel}</p>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="py-1">
            <button
              onClick={() => { setIsOpen(false); onLogout(); }}
              className="w-full text-left px-4 py-2.5 text-[13px] text-onsurface-variant hover:bg-surface-container transition-colors duration-200 flex items-center gap-3"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Đăng xuất
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
