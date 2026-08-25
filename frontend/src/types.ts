export interface Document {
  id: number;
  fileName: string;
  fileSize: number;
  fileType: string;
  chunkCount: number;
  createdAt: string;
  title?: string | null;
  documentNumber?: string | null;
  issuingBody?: string | null;
  issueDate?: string | null;
  effectiveDate?: string | null;
  sourceType?: "OFFICIAL" | "USER" | "FIXTURE" | null;
}

/** Structured citation returned by the backend. All legal fields nullable —
 * null means "not available", never fabricated. */
export interface SourceCitation {
  documentId?: number | null;
  content?: string | null;
  score?: number | null;
  chunkId?: number | null;
  article?: string | null;
  clause?: string | null;
  point?: string | null;
  documentTitle?: string | null;
  documentNumber?: string | null;
  sourceType?: string | null;
}

export type RagStrategy = "direct" | "corrective" | "web_search" | "no_evidence" | "blocked";

export interface ChatMessage {
  id?: number;
  sessionId: string;
  userMessage: string;
  aiResponse: string;
  sourceChunks?: string | null;
  sources?: SourceCitation[] | null;
  ragStrategy?: RagStrategy | null;
  confidence?: "high" | "medium" | "low" | null;
  documentId?: number | null;
  isStreaming?: boolean;
}

export interface LegalChunkDTO {
  id: number;
  ordinal: number;
  article?: string | null;
  clause?: string | null;
  point?: string | null;
  content: string;
}

export interface LegalDocumentDetail {
  documentId: number;
  fileName: string;
  title?: string | null;
  documentNumber?: string | null;
  issuingBody?: string | null;
  issueDate?: string | null;
  effectiveDate?: string | null;
  sourceType: "OFFICIAL" | "USER" | "FIXTURE";
  chunks: LegalChunkDTO[];
}

export interface ChatSession {
  sessionId: string;
  lastMessage: string;
  createdAt: string;
}