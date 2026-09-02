import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { v4 as uuidv4 } from "uuid";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";
import type { Document, ChatMessage as ChatMessageType, SourceCitation } from "../types";
import SourceCitations from "../components/SourceCitations";
import MessageBubble from "../components/MessageBubble";
import EvidenceState from "../components/EvidenceState";
import DocumentViewer from "../components/DocumentViewer";
import AppBar from "../components/AppBar";
import Sidebar from "../components/Sidebar";
import WelcomeScreen from "../components/WelcomeScreen";
import UserMenu from "../components/UserMenu";

export default function ChatPage() {
  const { token, username, logout } = useAuth();
  const queryClient = useQueryClient();

  const [sessionId, setSessionId] = useState<string>(() => {
    let id = localStorage.getItem("sessionId");
    if (!id) {
      id = uuidv4();
      localStorage.setItem("sessionId", id);
    }
    return id;
  });

  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [uploadError, setUploadError] = useState("");
  // Legal search state (Decision 15)
  interface DocumentSearchResult { id: number; fileName: string; title?: string | null; documentNumber?: string | null; }
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[]>([]);
  const [viewingSource, setViewingSource] = useState<SourceCitation | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch documents
  const { data: documents = [] } = useQuery<Document[]>({
    queryKey: ["documents", token],
    queryFn: async () => {
      if (!token) return [];
      const response = await fetch(`${API_BASE_URL}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Failed to fetch documents");
      return response.json();
    },
    enabled: !!token,
  });

  // Fetch chat history
  const historyQueryKey = ["chatHistory", sessionId, selectedDoc?.id];

  const fetchChatHistory = useCallback(async () => {
    if (!token) return [];
    let url = `${API_BASE_URL}/chat/history/${sessionId}`;
    if (selectedDoc?.id) {
      url = `${API_BASE_URL}/chat/history/${sessionId}/${selectedDoc.id}`;
    }
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("Failed to fetch chat history");
    return response.json();
  }, [sessionId, selectedDoc, token]);

  const { data: history = [] } = useQuery<ChatMessageType[]>({
    queryKey: historyQueryKey,
    queryFn: fetchChatHistory,
    enabled: !!token,
  });

  // Sync history to messages
  useEffect(() => {
    if (history.length > 0) {
      setMessages(history);
    }
  }, [history]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = () => {
    const newId = uuidv4();
    setSessionId(newId);
    localStorage.setItem("sessionId", newId);
    setMessages([]);
    setSelectedDoc(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ];
    if (!allowedTypes.includes(file.type)) {
      setUploadError("Only PDF, DOCX, and TXT files are supported");
      return;
    }

    setUploadError("");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...csrfHeaders(),
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.message || "Upload failed");
      }

      queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Error uploading document");
    }
  };

  const handleSendMessage = async () => {
    const textToSend = input.trim();
    if (!textToSend || loading) return;

    setInput("");
    setLoading(true);

    const payload = {
      sessionId,
      message: textToSend,
      documentId: selectedDoc?.id || null,
    };

    const userMsg: ChatMessageType = {
      sessionId,
      userMessage: textToSend,
      aiResponse: "",
      documentId: selectedDoc?.id || null,
    };

    const streamingPlaceholderId = Date.now();
    const streamingAiMsg: ChatMessageType = {
      id: streamingPlaceholderId,
      sessionId,
      userMessage: textToSend,
      aiResponse: "",
      sourceChunks: null,
      documentId: selectedDoc?.id || null,
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, streamingAiMsg]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/ask-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...csrfHeaders(),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Streaming response failed");
      }

      if (!response.body) {
        throw new Error("ReadableStream not supported");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue;

          let eventType = "";
          let dataStr = "";

          const lines = rawEvent.split("\n");
          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.replace("event:", "").trim();
            } else if (line.startsWith("data:")) {
              dataStr = line.replace("data:", "").trim();
            }
          }

          if (eventType === "metadata") {
            const meta = JSON.parse(dataStr);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingPlaceholderId
                  ? {
                      ...msg,
                      sourceChunks: meta.sourceChunks,
                      sources: Array.isArray(meta.sources) ? meta.sources : null,
                      ragStrategy: meta.ragStrategy ?? null,
                      confidence: meta.confidence ?? null,
                    }
                  : msg,
              ),
            );
          } else if (eventType === "chunk") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingPlaceholderId
                  ? { ...msg, aiResponse: msg.aiResponse + dataStr }
                  : msg,
              ),
            );
          } else if (eventType === "complete") {
            const finalSavedMsg: ChatMessageType = JSON.parse(dataStr);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingPlaceholderId
                  ? { ...finalSavedMsg, isStreaming: false }
                  : msg,
              ),
            );
            queryClient.invalidateQueries({ queryKey: historyQueryKey });
          } else if (eventType === "error") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingPlaceholderId
                  ? {
                      ...msg,
                      aiResponse: `❌ Error: ${dataStr}`,
                      isStreaming: false,
                    }
                  : msg,
              ),
            );
          }
        }
      }
    } catch (error: unknown) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingPlaceholderId
            ? {
                ...msg,
                aiResponse: `❌ Error: ${error instanceof Error ? error.message : "Unknown error"}`,
                isStreaming: false,
              }
            : msg,
        ),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-surface-dim">
      <AppBar
        onMenuClick={() => setSidebarOpen(true)}
        username={username}
        onLogout={logout}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          documents={documents}
          selectedDoc={selectedDoc}
          onSelectDoc={setSelectedDoc}
          onNewChat={handleNewChat}
          onUploadClick={() => fileInputRef.current?.click()}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages or Welcome */}
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <WelcomeScreen onUploadClick={() => fileInputRef.current?.click()} />
            ) : (
              <div className="px-6 py-6" role="log" aria-label="Lịch sử trò chuyện" tabIndex={0}>
                <div className="max-w-3xl mx-auto space-y-6">
                  {messages.map((msg, idx) => (
                    <div key={msg.id || idx} className="space-y-3">
                      <MessageBubble content={msg.userMessage} role="user" />
                      <MessageBubble content={msg.aiResponse} role="assistant" isStreaming={msg.isStreaming} />
                      {!msg.isStreaming && (
                        <EvidenceState ragStrategy={msg.ragStrategy} confidence={msg.confidence} />
                      )}
                      <SourceCitations
                        sources={msg.sources}
                        sourceChunks={msg.sourceChunks}
                        onViewSource={(s) => setViewingSource(s)}
                      />
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            )}
          </div>


          {/* Upload error */}
          {uploadError && (
            <div className="mx-6 mb-3 px-4 py-2.5 bg-[#fce8e6] border border-[#f5c6cb] rounded-material text-[#a50e0e] text-[13px] flex items-center gap-2" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#d93025">
                <path d="M12 2L1 21h22L12 2zm0 14a1 1 0 110 2 1 1 0 010-2zm1-8h-2v6h2V8z" />
              </svg>
              {uploadError}
            </div>
          )}

          {/* Input — always visible */}
          <div className="border-t border-outline px-6 py-4 bg-surface">
            <div className="max-w-3xl mx-auto">
              <div className="flex gap-3 items-end">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={selectedDoc ? `Hỏi về ${selectedDoc.fileName}...` : "Nhập tin nhắn... (Shift+Enter dòng mới)"}
                  className="flex-1 px-4 py-3 border border-outline rounded-material-lg resize-none focus:outline-none focus:border-google-blue focus:ring-1 focus:ring-google-blue text-[14px] bg-surface-container"
                  rows={1}
                  disabled={loading}
                  aria-label="Nhập tin nhắn"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={loading || !input.trim()}
                  className="w-12 h-12 bg-google-blue hover:bg-google-blueDark disabled:bg-on-surface-disabled text-white rounded-material-full flex items-center justify-center transition-all duration-200 shadow-material-btn hover:shadow-material-btn-hover disabled:shadow-none"
                  aria-label="Gửi tin nhắn"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* Document viewer */}
          {viewingSource && (
            <DocumentViewer
              citation={viewingSource}
              token={token}
              onClose={() => setViewingSource(null)}
            />
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.docx"
            className="hidden"
            onChange={handleFileUpload}
          />
        </div>
      </div>
    </div>
  );
}
