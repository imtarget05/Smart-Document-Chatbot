import { useChatSessions, relativeTime } from "../hooks/useChatSessions";

interface SessionListProps {
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
}

export default function SessionList({ activeSessionId, onSelectSession }: SessionListProps) {
  const { data: sessions = [], isLoading } = useChatSessions();

  if (isLoading) {
    return <p className="px-3 py-2 text-[12px] text-onsurface-muted">Đang tải...</p>;
  }

  if (sessions.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <p className="px-3 py-1.5 text-[11px] text-onsurface-muted font-medium uppercase tracking-wider">
        Cuộc trò chuyện gần đây
      </p>
      <div className="space-y-0.5">
        {sessions.map((session) => (
          <button
            key={session.sessionId}
            onClick={() => onSelectSession(session.sessionId)}
            className={`w-full text-left px-3 py-2 rounded-material transition ${
              activeSessionId === session.sessionId
                ? "bg-google-blue/10 text-google-blue"
                : "hover:bg-surface-container text-onsurface"
            }`}
          >
            <p className="text-[12px] truncate font-medium">
              🕐 {session.lastMessage || "Cuộc trò chuyện"}
            </p>
            <p className="text-[11px] text-onsurface-muted">
              {relativeTime(session.updatedAt)} • {session.messageCount} tin nhắn
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
