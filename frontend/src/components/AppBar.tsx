interface AppBarProps {
  onMenuClick: () => void;
  username?: string | null;
  onLogout: () => void;
}

export default function AppBar({ onMenuClick, username, onLogout }: AppBarProps) {
  const initials = username ? username.slice(0, 2).toUpperCase() : "U";

  return (
    <header className="h-appbar bg-surface border-b border-outline flex items-center justify-between px-4 shrink-0">
      {/* Left: menu + logo */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden w-10 h-10 rounded-material-full hover:bg-surface-container flex items-center justify-center transition-colors duration-200"
          aria-label="Mở menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-onsurface-variant">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-google-blue rounded-material flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="white" opacity="0.3" />
              <polyline points="14 2 14 8 20 8" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="16" y1="13" x2="8" y2="13" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="16" y1="17" x2="8" y2="17" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-[20px] text-onsurface font-normal tracking-tight hidden sm:block">
            Smart Document
          </h1>
        </div>
      </div>

      {/* Right: user menu */}
      <div className="relative group">
        <button
          className="w-9 h-9 rounded-material-full bg-google-blue text-white text-[13px] font-medium flex items-center justify-center hover:shadow-material-btn transition-shadow duration-200"
          aria-label="Menu người dùng"
        >
          {initials}
        </button>

        {/* Dropdown */}
        <div className="absolute right-0 top-full mt-2 w-56 bg-surface border border-outline rounded-material-lg shadow-material-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
          <div className="px-4 py-3 border-b border-outline">
            <p className="text-[13px] text-onsurface font-medium truncate">{username || "User"}</p>
          </div>
          <button
            onClick={onLogout}
            className="w-full text-left px-4 py-2.5 text-[13px] text-onsurface-variant hover:bg-surface-container transition-colors duration-200 flex items-center gap-2"
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
    </header>
  );
}
