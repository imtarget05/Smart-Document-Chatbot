import { useAuth, API_BASE_URL } from "../context/AuthContext";
import AgentChat from "../components/AgentChat";
import AdkDemoCard from "../components/AdkDemoCard";

export default function AgentChatPage() {
  const { token } = useAuth();
  const sessionId = localStorage.getItem("sessionId") || "default";

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="p-4 border-b border-gray-200 bg-white">
        <AdkDemoCard apiBaseUrl={API_BASE_URL} />
      </div>
      <div className="flex-1 min-h-0">
        <AgentChat token={token || ""} sessionId={sessionId} documentIds={[]} />
      </div>
    </div>
  );
}
