import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import ConceptMap from './ConceptMap';
import { Document } from '../App';

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8080/api';

export interface ChatMessage {
  id?: number;
  sessionId: string;
  userMessage: string;
  aiResponse: string;
  sourceChunks?: string | null;
  documentId?: number | null;
  documentIds?: number[] | null;
  isStreaming?: boolean;
}

interface ChatWindowProps {
  sessionId: string;
  documentId?: number | null;
  documentIds?: number[];
  chatMode: 'single' | 'multi';
  document?: Document | null;
  documents?: Document[];
  onUpdateDocument?: (updatedDoc: Document) => void;
}

function ChatWindow({
  sessionId,
  documentId = null,
  documentIds = [],
  chatMode,
  document = null,
  documents = [],
  onUpdateDocument = () => {}
}: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'mindmap'>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // React Query for history management
  const historyQueryKey = chatMode === 'single' && documentId
    ? ['chatHistory', sessionId, documentId]
    : ['chatHistory', sessionId];

  const fetchChatHistoryFn = useCallback(async () => {
    let url = `${API_BASE_URL}/chat/history/${sessionId}`;
    if (chatMode === 'single' && documentId) {
      url = `${API_BASE_URL}/chat/history/${sessionId}/${documentId}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch chat history');
    }
    const data: ChatMessage[] = await response.json();
    
    // Filter logic for multi mode
    if (chatMode === 'multi' && documentIds && documentIds.length > 0) {
      return data.filter(msg => {
        if (!msg.documentIds) return false;
        return msg.documentIds.some(id => documentIds.includes(id));
      });
    }
    return data;
  }, [sessionId, documentId, documentIds, chatMode]);

  const { data: history = [] } = useQuery<ChatMessage[]>({
    queryKey: historyQueryKey,
    queryFn: fetchChatHistoryFn,
  });

  // Sync React Query cached history to local messages state, preserving streaming items
  useEffect(() => {
    if (history.length > 0) {
      setMessages(history);
    } else {
      setMessages([]);
    }
  }, [history]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // If the document is updated in the background (insights populated), poll or fetch again
  useEffect(() => {
    if (chatMode === 'single' && document && (!document.summary || !document.suggestedQuestions)) {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/documents/${documentId}`);
          if (res.ok) {
            const freshDoc = await res.json();
            if (freshDoc.summary && freshDoc.suggestedQuestions) {
              onUpdateDocument(freshDoc);
              queryClient.invalidateQueries({ queryKey: ['documents'] });
              clearInterval(interval);
            }
          }
        } catch (e) {
          console.error('Error polling document updates:', e);
        }
      }, 3000);
      return () => clearInterval(interval);
    }
    return;
  }, [document, chatMode, documentId, onUpdateDocument, queryClient]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (customMessage?: string) => {
    const textToSend = customMessage || input;
    if (!textToSend.trim()) return;

    setInput('');
    setLoading(true);

    // 1. Prepare streaming payload
    const payload: Record<string, any> = {
      sessionId,
      message: textToSend,
    };

    if (chatMode === 'multi') {
      payload.documentIds = documentIds;
    } else {
      payload.documentId = documentId;
    }

    // 2. Add local optimistic message for user and placeholder for streaming AI response
    const userMsg: ChatMessage = {
      sessionId,
      userMessage: textToSend,
      aiResponse: '',
      documentId: chatMode === 'single' ? documentId : null,
      documentIds: chatMode === 'multi' ? documentIds : null
    };

    const streamingPlaceholderId = Date.now();
    const streamingAiMsg: ChatMessage = {
      id: streamingPlaceholderId,
      sessionId,
      userMessage: textToSend,
      aiResponse: '',
      sourceChunks: null,
      documentId: chatMode === 'single' ? documentId : null,
      documentIds: chatMode === 'multi' ? documentIds : null,
      isStreaming: true
    };

    setMessages(prev => [...prev, userMsg, streamingAiMsg]);

    try {
      // 3. Initiate SSE connection via POST
      const response = await fetch(`${API_BASE_URL}/chat/ask-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Streaming response failed');
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported in this browser');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        
        // Save the last block if it is incomplete
        buffer = events.pop() || '';

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue;

          let eventType = '';
          let dataStr = '';

          const lines = rawEvent.split('\n');
          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.replace('event:', '').trim();
            } else if (line.startsWith('data:')) {
              dataStr = line.replace('data:', '').trim();
            }
          }

          if (eventType === 'metadata') {
            const meta = JSON.parse(dataStr);
            setMessages(prev => prev.map(msg => 
              msg.id === streamingPlaceholderId 
                ? { 
                    ...msg, 
                    sourceChunks: meta.sourceChunks, 
                    aiResponse: meta.prefix || '' 
                  }
                : msg
            ));
          } else if (eventType === 'chunk') {
            setMessages(prev => prev.map(msg => 
              msg.id === streamingPlaceholderId 
                ? { ...msg, aiResponse: msg.aiResponse + dataStr }
                : msg
            ));
          } else if (eventType === 'complete') {
            const finalSavedMsg: ChatMessage = JSON.parse(dataStr);
            setMessages(prev => prev.map(msg => 
              msg.id === streamingPlaceholderId 
                ? { ...finalSavedMsg, isStreaming: false }
                : msg
            ));
            // Invalidate React Query chat cache so that background transitions are clean
            queryClient.invalidateQueries({ queryKey: historyQueryKey });
          } else if (eventType === 'error') {
            console.error('SSE backend streaming error:', dataStr);
            setMessages(prev => prev.map(msg => 
              msg.id === streamingPlaceholderId 
                ? { ...msg, aiResponse: msg.aiResponse + `\n\n❌ [Error during generation: ${dataStr}]`, isStreaming: false }
                : msg
            ));
          }
        }
      }

    } catch (error: any) {
      console.error('Error sending message stream:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === streamingPlaceholderId 
          ? { ...msg, aiResponse: `❌ Error sending message. Please make sure the service is online. Details: ${error.message}`, isStreaming: false }
          : msg
      ));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const parseSuggestedQuestions = (questionsStr?: string | null) => {
    if (!questionsStr) return [];
    try {
      return JSON.parse(questionsStr) as string[];
    } catch (e) {
      console.error('Error parsing suggested questions', e);
      return [];
    }
  };

  const parsedQuestions = chatMode === 'single' && document ? parseSuggestedQuestions(document.suggestedQuestions) : [];

  if (chatMode === 'single' && document && document.status && document.status !== 'READY') {
    if (document.status === 'PROCESSING') {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50/50">
          <div className="relative w-20 h-20 mb-6">
            <div className="absolute inset-0 rounded-full border-4 border-dashed border-indigo-200 animate-spin duration-1000"></div>
            <div className="absolute inset-2 rounded-full border-4 border-indigo-500/20 animate-pulse"></div>
            <span className="absolute inset-0 flex items-center justify-center text-3xl animate-bounce">⚙️</span>
          </div>
          <h3 className="text-lg font-bold text-gray-800">Apache Airflow ETL in progress</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-sm text-center leading-relaxed font-semibold">
            The data pipeline is actively parsing pages, generating semantic vector embeddings via Gemini, and indexing metadata into Qdrant.
          </p>
          <div className="mt-6 flex items-center gap-3 bg-white px-4 py-2.5 rounded-xl border border-gray-150 shadow-sm text-xs font-bold text-gray-600">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping"></span>
            DAG Run: <span className="font-mono text-indigo-600">document_etl</span>
          </div>
        </div>
      );
    }

    if (document.status === 'FAILED') {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50/50">
          <div className="text-5xl mb-4">❌</div>
          <h3 className="text-lg font-bold text-gray-800">ETL Pipeline Failed</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-sm text-center leading-relaxed font-semibold">
            The Airflow DAG failed during document ingestion. Please check the workflow status and logs in the Airflow dashboard.
          </p>
          <div className="mt-6">
            <a
              href="http://localhost:8085"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition inline-block"
            >
              Open Airflow Dashboard
            </a>
          </div>
        </div>
      );
    }
  }

  return (
    <div className="flex flex-col h-full bg-white relative">
      {/* Subheader / Tab Switcher (Only in single mode) */}
      {chatMode === 'single' && document && (
        <div className="bg-gray-50 border-b border-gray-200 px-6 py-2.5 flex items-center justify-between">
          <div className="flex bg-gray-200/80 p-0.5 rounded-lg border border-gray-200/30">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 ${
                activeTab === 'chat'
                  ? 'bg-white text-indigo-600 shadow-sm font-bold'
                  : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              💬 AI Chat
            </button>
            <button
              onClick={() => setActiveTab('mindmap')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 ${
                activeTab === 'mindmap'
                  ? 'bg-white text-indigo-600 shadow-sm font-bold'
                  : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              🕸️ Concept Map
            </button>
          </div>
          
          <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider bg-white px-2 py-1 rounded-md border border-gray-100">
            {document.fileType} File
          </div>
        </div>
      )}

      {/* Render Concept Map Visualizer */}
      {chatMode === 'single' && activeTab === 'mindmap' ? (
        <ConceptMap
          documentId={documentId!}
          documentName={document?.fileName || 'Document'}
          onAskAI={(concept) => {
            setActiveTab('chat');
            setInput(`Explain the core relevance of "${concept}" inside the context of this document.`);
          }}
        />
      ) : (
        <>
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50/20">
            {messages.length === 0 ? (
              chatMode === 'single' && document ? (
                /* Premium Dashboard Insights (Executive Summary & Suggested Questions) */
                <div className="max-w-2xl mx-auto space-y-6 py-4 animate-fade-in">
                  <div className="text-center mb-6">
                    <span className="text-3xl">✨</span>
                    <h3 className="text-lg font-bold text-gray-800 mt-2">Welcome to AI Document Insights</h3>
                    <p className="text-xs text-gray-400 mt-1">Explore parsed summaries and custom concept questions generated for this file.</p>
                  </div>

                  {/* Summary Card */}
                  <div className="bg-white rounded-2xl border border-gray-200/70 p-5 shadow-sm shadow-gray-100/50">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                      <span>📄</span> Executive Summary
                    </h4>
                    {document.summary ? (
                      <div className="text-sm text-gray-600 leading-relaxed space-y-2 whitespace-pre-line font-medium">
                        {document.summary}
                      </div>
                    ) : (
                      /* Summary Skeleton Loading */
                      <div className="space-y-2 animate-pulse">
                        <div className="h-4 bg-gray-100 rounded-md w-3/4"></div>
                        <div className="h-4 bg-gray-100 rounded-md w-5/6"></div>
                        <div className="h-4 bg-gray-100 rounded-md w-2/3"></div>
                        <div className="text-xs text-gray-400 italic mt-2">AI is reading and parsing this document for insights...</div>
                      </div>
                    )}
                  </div>

                  {/* Suggested Questions Panel */}
                  <div className="bg-white rounded-2xl border border-gray-200/70 p-5 shadow-sm shadow-gray-100/50">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <span>💡</span> AI Suggested Questions
                    </h4>
                    {document.suggestedQuestions ? (
                      <div className="flex flex-col gap-2.5">
                        {parsedQuestions.map((q, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSendMessage(q)}
                            className="text-left w-full p-3 rounded-xl border border-gray-100 hover:border-indigo-200 bg-gray-50/50 hover:bg-indigo-50/20 text-xs font-semibold text-gray-700 hover:text-indigo-600 transition-all duration-200 shadow-sm shadow-gray-50 flex items-center gap-2"
                          >
                            <span className="text-indigo-400">❓</span> {q}
                          </button>
                        ))}
                      </div>
                    ) : (
                      /* Questions Skeleton Loading */
                      <div className="space-y-3 animate-pulse">
                        <div className="h-10 bg-gray-100 rounded-xl w-full"></div>
                        <div className="h-10 bg-gray-100 rounded-xl w-full"></div>
                        <div className="h-10 bg-gray-100 rounded-xl w-full"></div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Multi-File Welcome Screen */
                <div className="flex items-center justify-center h-full text-gray-400 bg-gray-50/10">
                  <div className="text-center p-8 max-w-md">
                    <div className="text-5xl mb-4">🔮</div>
                    <h3 className="text-base font-bold text-gray-800 mb-1">Multi-File Synthesized RAG Chat</h3>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      You are chatting with <strong>{documents ? documents.length : 0} documents</strong> simultaneously.
                      Your queries will perform parallel semantic searches across all collections. The AI will synthesize the context and tag sources automatically.
                    </p>
                  </div>
                </div>
              )
            ) : (
              messages.map((msg, idx) => (
                <div key={msg.id || idx} className="space-y-4">
                  {/* User Message */}
                  <div className="flex justify-end">
                    <div className="max-w-xs lg:max-w-md bg-gradient-to-tr from-indigo-600 to-indigo-700 text-white p-3.5 rounded-2xl rounded-br-none shadow-md shadow-indigo-100/55">
                      <p className="text-sm font-medium leading-relaxed">{msg.userMessage}</p>
                    </div>
                  </div>

                  {/* AI Response */}
                  <div className="flex justify-start">
                    <div className="max-w-xs lg:max-w-xl bg-white border border-gray-200/80 text-gray-800 p-4 rounded-2xl rounded-bl-none shadow-sm shadow-gray-100/30">
                      <div className="text-sm leading-relaxed whitespace-pre-line font-medium text-gray-700">
                        {msg.aiResponse || (
                          <div className="typing flex items-center gap-1 py-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"></span>
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce delay-75"></span>
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce delay-150"></span>
                          </div>
                        )}
                      </div>
                      
                      {/* Sources Drawer */}
                      {msg.sourceChunks && (
                        <details className="mt-3.5 border-t border-gray-100 pt-3 group">
                          <summary className="cursor-pointer text-xs font-bold text-gray-400 hover:text-indigo-600 transition flex items-center gap-1.5 select-none">
                            <span>📚</span> Context Sources
                          </summary>
                          <div className="mt-2.5 space-y-2.5 max-h-48 overflow-y-auto pr-1">
                            {msg.sourceChunks.split('---').map((chunk, i) => {
                              const match = chunk.trim().match(/^\[(.*?)\] (.*)$/s);
                              const docName = match ? match[1] : null;
                              const textContent = match ? match[2] : chunk;
                              
                              return (
                                <div key={i} className="p-2.5 rounded-xl bg-gray-50 border border-gray-100 text-left">
                                  {docName && (
                                    <span className="text-[9px] font-bold bg-indigo-50 border border-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded-md mb-1.5 inline-block">
                                      {docName}
                                    </span>
                                  )}
                                  <p className="text-xs text-gray-500 leading-relaxed font-medium italic">
                                    "{textContent.trim()}"
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200/80 p-4 bg-white shadow-lg">
            <div className="flex gap-3 max-w-3xl mx-auto">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  chatMode === 'multi'
                    ? "Ask a question synthesizing across selected documents..."
                    : "Ask a question about the document... (Shift+Enter for new line)"
                }
                className="flex-1 p-3 border border-gray-200 rounded-xl resize-none focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm font-medium bg-gray-50/30"
                rows={2}
                disabled={loading}
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={loading || !input.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white px-5 rounded-xl transition duration-200 font-bold text-xs shadow-md shadow-indigo-100 hover:shadow-indigo-200 flex items-center justify-center flex-shrink-0"
              >
                Send
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ChatWindow;
