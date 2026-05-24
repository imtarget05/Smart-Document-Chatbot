import { useState } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import ChatWindow from './components/ChatWindow';
import DocumentList from './components/DocumentList';
import { v4 as uuidv4 } from 'uuid';
import { useQuery } from '@tanstack/react-query';

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8080/api';

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

function App() {
  const [sessionId] = useState<string>(() => {
    let id = localStorage.getItem('sessionId');
    if (!id) {
      id = uuidv4();
      localStorage.setItem('sessionId', id);
    }
    return id;
  });

  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);

  // New states for Multi-Document selection
  const [chatMode, setChatMode] = useState<'single' | 'multi'>('single');
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);

  // Fetch documents using TanStack Query
  const { data: documents = [], refetch: fetchDocuments } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      return response.json();
    },
  });

  const handleDocumentUploaded = () => {
    fetchDocuments();
  };

  const handleDocumentDeleted = (id: number) => {
    setSelectedDocumentIds(prev => prev.filter(x => x !== id));
    if (selectedDocument?.id === id) {
      setSelectedDocument(null);
    }
  };

  const handleToggleChatMode = (mode: 'single' | 'multi') => {
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
  };

  const handleToggleDocumentSelect = (id: number) => {
    setSelectedDocumentIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSelectAllDocuments = () => {
    if (selectedDocumentIds.length === documents.length) {
      setSelectedDocumentIds([]);
    } else {
      setSelectedDocumentIds(documents.map(d => d.id));
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 overflow-hidden bg-white border-r border-gray-200 flex flex-col`}>
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <span>📚</span> Smart Doc Chat
          </h1>
          <p className="text-xs text-gray-400 mt-1">Session ID: {sessionId.slice(0, 8)}...</p>
        </div>

        <DocumentUpload onDocumentUploaded={handleDocumentUploaded} />

        <div className="flex-1 overflow-y-auto">
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
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-150 rounded-lg transition"
            aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          >
            {sidebarOpen ? '←' : '→'}
          </button>
          <div className="flex-1 ml-4">
            {chatMode === 'multi' && (
              <div>
                <h2 className="text-base font-semibold text-gray-800">Multi-File Chat Mode</h2>
                <p className="text-xs text-gray-500">
                  Searching over {selectedDocumentIds.length} selected document{selectedDocumentIds.length !== 1 ? 's' : ''}
                </p>
              </div>
            )}
            {chatMode === 'single' && selectedDocument && (
              <div>
                <h2 className="text-base font-semibold text-gray-800">{selectedDocument.fileName}</h2>
                <p className="text-xs text-gray-500">{selectedDocument.chunkCount} chunks • single document mode</p>
              </div>
            )}
            {chatMode === 'single' && !selectedDocument && (
              <p className="text-gray-500 text-sm">Select a document in the sidebar to begin</p>
            )}
          </div>
        </div>

        {/* Chat Content */}
        {chatMode === 'multi' ? (
          selectedDocumentIds.length > 0 ? (
            <ChatWindow
              sessionId={sessionId}
              documentIds={selectedDocumentIds}
              chatMode="multi"
              documents={documents.filter(d => selectedDocumentIds.includes(d.id))}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400 bg-gray-50">
              <div className="text-center p-8 max-w-sm">
                <div className="text-4xl mb-3">📁</div>
                <p className="text-base font-semibold text-gray-700 mb-1">No documents selected</p>
                <p className="text-xs text-gray-500 leading-relaxed">
                  Toggle selection checkboxes next to documents in the sidebar to start a cross-file synthesized chat.
                </p>
              </div>
            </div>
          )
        ) : selectedDocument ? (
          <ChatWindow
            sessionId={sessionId}
            documentId={selectedDocument.id}
            chatMode="single"
            document={selectedDocument}
            onUpdateDocument={(updatedDoc) => {
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
      </div>
    </div>
  );
}

export default App;
