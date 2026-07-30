export interface Document {
  id: number;
  fileName: string;
  fileSize: number;
  fileType: string;
  chunkCount: number;
  createdAt: string;
}

export interface ChatMessage {
  id?: number;
  sessionId: string;
  userMessage: string;
  aiResponse: string;
  sourceChunks?: string | null;
  documentId?: number | null;
  isStreaming?: boolean;
}

export interface ChatSession {
  sessionId: string;
  lastMessage: string;
  createdAt: string;
}