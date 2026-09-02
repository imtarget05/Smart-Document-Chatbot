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
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <span className="text-xl">📚</span>
          <h1 className="text-lg font-semibold text-gray-800">Smart Document Chat</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{username}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700 transition"
            aria-label="Đăng xuất"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Document selector bar */}
      <div className="flex items-center gap-3 px-6 py-2 border-b border-gray-100 bg-gray-50">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.docx,.txt"
          />
          <span className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded-lg transition" role="button" aria-label="Tải lên tài liệu">
            📎 Upload
          </span>
        </label>
        {documents.length > 0 && (
          <select
            value={selectedDoc?.id || ""}
            onChange={(e) => {
              const doc = documents.find((d) => d.id === Number(e.target.value));
              setSelectedDoc(doc || null);
            }}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300"
          >
            <option value="">Select a document...</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.fileName} ({doc.chunkCount} chunks)
              </option>
            ))}
          </select>
        )}
        {uploadError && (
          <span className="text-xs text-red-500" role="alert">{uploadError}</span>
        )}
        <button
          onClick={handleNewChat}
          className="ml-auto text-xs text-gray-500 hover:text-gray-700 transition"
          aria-label="Tạo cuộc trò chuyện mới"
        >
          + New Chat
        </button>
      </div>

      {/* Legal search (Decision 15) */}
      <div className="px-6 py-2 border-b border-gray-100 bg-white">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!searchQuery.trim()) { setSearchResults([]); return; }
            try {
              const response = await fetch(
                `${API_BASE_URL}/documents/search?q=${encodeURIComponent(searchQuery)}`,
                { headers: { Authorization: `Bearer ${token}` } }
              );
              setSearchResults(response.ok ? await response.json() : []);
            } catch {
              setSearchResults([]);
            }
          }}
          className="flex items-center gap-2"
        >
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm văn bản pháp luật (tên, số hiệu, Điều...)"
            className="flex-1 max-w-md text-xs border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-gray-300"
          />
          <button type="submit" className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700">
            Tìm kiếm
          </button>
        </form>
        {searchResults.length > 0 && (
          <ul className="mt-2 space-y-1">
            {searchResults.map((r) => (
              <li key={r.id} className="flex items-center gap-2 text-xs text-gray-600">
                <button
                  onClick={() => {
                    const doc = documents.find((d) => d.id === r.id);
                    setSelectedDoc(doc || null);
                    setSearchResults([]);
                  }}
                  className="text-blue-600 hover:underline"
                >
                  Mở
                </button>
                <span className="font-medium">{r.title || r.fileName}</span>
                {r.documentNumber && <span className="text-gray-400">Số: {r.documentNumber}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6" role="log" aria-label="Lịch sử trò chuyện" tabIndex={0}>
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 py-20" role="status">
              <span className="text-4xl mb-3">💬</span>
              <p className="text-sm font-medium">Start a conversation</p>
              <p className="text-xs mt-1">
                Upload a document and ask questions about it
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={msg.id || idx} className="space-y-3">
                <MessageBubble content={msg.userMessage} role="user" />
                <MessageBubble content={msg.aiResponse} role="assistant" isStreaming={msg.isStreaming} />

                {/* Evidence state + structured citations */}
                {!msg.isStreaming && (
                  <EvidenceState ragStrategy={msg.ragStrategy} confidence={msg.confidence} />
                )}
                <SourceCitations
                  sources={msg.sources}
                  sourceChunks={msg.sourceChunks}
                  onViewSource={(s) => setViewingSource(s)}
                />
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Document / evidence viewer */}
      {viewingSource && (
        <DocumentViewer
          citation={viewingSource}
          token={token}
          onClose={() => setViewingSource(null)}
        />
      )}

      {/* Input */}
      <div className="border-t border-gray-200 px-6 py-4 bg-white">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-3 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                selectedDoc
                  ? `Ask about ${selectedDoc.fileName}...`
                  : "Type a message... (Shift+Enter for new line)"
              }
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl resize-none focus:outline-none focus:border-gray-400 text-sm bg-gray-50"
              rows={1}
              disabled={loading}
              aria-label="Nhập tin nhắn"
            />
            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim()}
              className="px-5 py-3 bg-gray-800 hover:bg-gray-900 disabled:bg-gray-300 text-white rounded-xl text-sm font-medium transition"
              aria-label="Gửi tin nhắn"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}