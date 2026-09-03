import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export interface ChatSession {
  sessionId: string;
  lastMessage: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
}

interface SessionsResponse {
  sessions: ChatSession[];
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} giờ trước`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days} ngày trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

export { relativeTime };

export function useChatSessions() {
  return useQuery<ChatSession[]>({
    queryKey: ["chatSessions"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/chat/sessions`, {
        headers: { ...(await csrfHeaders()) },
        credentials: "include",
      });
      if (!res.ok) return [];
      const data: SessionsResponse = await res.json();
      return data.sessions ?? [];
    },
    staleTime: 60_000,
  });
}
