export interface Document {
  id: number;
  fileName: string;
  fileSize: number;
  fileType: string;
  chunkCount: number;
  status: 'PROCESSING' | 'READY' | 'FAILED';
  summary?: string;
  suggestedQuestions?: string;
  vectorCollectionId?: string;
  createdAt: string;
}

export interface ChatSession {
  sessionId: string;
  lastMessage: string;
  createdAt: string;
}