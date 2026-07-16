import { useState, useCallback } from 'react';
import { useAuth, API_BASE_URL } from '../context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { v4 as uuidv4 } from 'uuid';
import ChatWindow from '../components/ChatWindow';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import ErrorBoundary from '../components/ErrorBoundary';
import type { Document, ChatSession } from '../types';

export default function ClassicChatPage() {
  const { token } = useAuth();

  const [sessionId, setSessionId] = useState<string>(() => {
    let id = localStorage.getItem('sessionId');
    if (!id) {
      id = uuidv4();
      localStorage.setItem('sessionId', id);
    }
    return id;
  });

  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [sidebarTab, setSidebarTab] = useState<'documents' | 'history'>('documents');
  const [chatMode, setChatMode] = useState<'single' | 'multi'>('single');
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);

  const { data: documents = [], refetch: fetchDocuments } = useQuery<Document[]>({
    queryKey: ['documents', token],
    queryFn: async () => {
      if (!token) return [];
      const response = await fetch(`${API_BASE_URL}/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 401) throw new Error('Session expired');
      if (!response.ok) throw new Error('Failed to fetch documents');
      return response.json();
    },
    enabled: !!token,
  });

  const { data: sessions = [], refetch: fetchSessions } = useQuery<ChatSession[]>({
    queryKey: ['chatSessions', token],
    queryFn: async () => {
      if (!token) return [];
      const response = await fetch(`${API_BASE_URL}/chat/sessions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch sessions');
      return response.json();
    },
    enabled: !!token && sidebarTab === 'history',
  });

  const handleNewChat = useCallback(() => {
    const newId = uuidv4();
    setSessionId(newId);
    localStorage.setItem('sessionId', newId);
    setSelectedDocument(null);
    setSelectedDocumentIds([]);
  }, []);

  const handleDocumentUploaded = useCallback(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleDocumentDeleted = useCallback((id: number) => {
    setSelectedDocumentIds(prev => prev.filter(x => x !== id));
    if (selectedDocument?.id === id) {
      setSelectedDocument(null);
    }
  }, [selectedDocument]);

  const handleToggleChatMode = useCallback((mode: 'single' | 'multi') => {
    setChatMode(mode);
    if (mode === 'single') {
      if (selectedDocumentIds.length > 0) {
        const firstDoc = documents.find(d => d.id === selectedDocumentIds[0]);
        setSelectedDocument(firstDoc || null);
      }
    } else {
      if (selectedDocument) {
        setSelectedDocumentIds([selectedDocument.id]);
      }
      setSelectedDocument(null);
    }
  }, [selectedDocumentIds, selectedDocument, documents]);

  const handleToggleDocumentSelect = useCallback((id: number) => {
    setSelectedDocumentIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  }, []);

  const handleSelectAllDocuments = useCallback(() => {
    if (selectedDocumentIds.length === documents.length) {
      setSelectedDocumentIds([]);
    } else {
      setSelectedDocumentIds(documents.map(d => d.id));
    }
  }, [selectedDocumentIds, documents]);

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
        <div className="p-3 space-y-3 border-b border-gray-200">
          <button
            onClick={handleNewChat}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2"
          >
            <span>+</span> New Conversation
          </button>

          <div className="flex bg-gray-100 p-1 rounded-xl border border-gray-200/50">
            <button
              onClick={() => setSidebarTab('documents')}
              className={`flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all ${
                sidebarTab === 'documents' ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              DOCUMENTS
            </button>
            <button
              onClick={() => {
                setSidebarTab('history');
                fetchSessions();
              }}
              className={`flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all ${
                sidebarTab === 'history' ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              HISTORY
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {sidebarTab === 'documents' ? (
            <>
              <DocumentUpload onDocumentUploaded={handleDocumentUploaded} />
              <DocumentList
                documents={documents}
                selectedDocument={selectedDocument}
                onSelectDocument={(doc) => {
                  setSelectedDocument(doc);
                  setChatMode('single');
                }}
                onDocumentDeleted={handleDocumentDeleted}
                chatMode={chatMode}
                onToggleChatMode={handleToggleChatMode}
                selectedDocumentIds={selectedDocumentIds}
                onToggleDocumentSelect={handleToggleDocumentSelect}
                onSelectAllDocuments={handleSelectAllDocuments}
              />
            </>
          ) : (
            <div className="p-3 space-y-2">
              {sessions.length === 0 ? (
                <div className="text-center py-10">
                  <span className="text-3xl block mb-2">📥</span>
                  <p className="text-xs text-gray-400 font-medium">No previous conversations yet.</p>
                </div>
              ) : (
                sessions.map((s) => (
                  <button
                    key={s.sessionId}
                    onClick={() => {
                      setSessionId(s.sessionId);
                      localStorage.setItem('sessionId', s.sessionId);
                    }}
                    className={`w-full text-left p-3 rounded-xl border transition-all duration-200 group ${
                      sessionId === s.sessionId
                        ? 'bg-indigo-50 border-indigo-200'
                        : 'bg-white border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-bold text-gray-400 uppercase tracking-tighter">
                        {new Date(s.createdAt).toLocaleDateString()}
                      </span>
                      {sessionId === s.sessionId && (
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
                      )}
                    </div>
                    <p className={`text-xs font-semibold truncate ${
                      sessionId === s.sessionId ? 'text-indigo-700' : 'text-gray-700'
                    }`}>
                      {s.lastMessage || 'Empty conversation'}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-1 truncate opacity-60">
                      ID: {s.sessionId.substring(0, 8)}...
                    </p>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between flex-shrink-0">
          <div className="flex-1">
            {chatMode === 'multi' && selectedDocumentIds.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-gray-800">Multi-File Chat Mode</h2>
                <p className="text-xs text-gray-500">
                  Searching over {selectedDocumentIds.length} selected document{selectedDocumentIds.length !== 1 ? 's' : ''}
                </p>
              </div>
            )}
            {chatMode === 'single' && selectedDocument && (
              <div>
                <h2 className="text-sm font-semibold text-gray-800">{selectedDocument.fileName}</h2>
                <p className="text-xs text-gray-500">{selectedDocument.chunkCount} chunks • single document mode</p>
              </div>
            )}
            {chatMode === 'single' && !selectedDocument && selectedDocumentIds.length === 0 && (
              <p className="text-gray-500 text-sm font-semibold">Select a document in the sidebar to begin</p>
            )}
          </div>
        </div>

        <ErrorBoundary>
          {chatMode === 'multi' && selectedDocumentIds.length > 0 ? (
            <ChatWindow
              sessionId={sessionId}
              documentIds={selectedDocumentIds}
              chatMode="multi"
              documents={documents.filter(d => selectedDocumentIds.includes(d.id))}
            />
          ) : selectedDocument ? (
            <ChatWindow
              sessionId={sessionId}
              documentId={selectedDocument.id}
              chatMode="single"
              document={selectedDocument}
              onUpdateDocument={(updatedDoc: Document) => {
                setSelectedDocument(updatedDoc);
              }}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400 bg-gray-50">
              <div className="text-center p-8 max-w-sm">
                <div className="text-4xl mb-3">📄</div>
                <p className="text-base font-semibold text-gray-700 mb-1">No document selected</p>
                <p className="text-xs text-gray-500 leading-relaxed">
                  Upload a document (PDF, Word, TXT) or select an existing one from the sidebar to view insights and start chatting.
                </p>
              </div>
            </div>
          )}
        </ErrorBoundary>
      </div>
    </div>
  );
}