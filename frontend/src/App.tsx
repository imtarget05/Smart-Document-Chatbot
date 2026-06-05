import { useState } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import ChatWindow from './components/ChatWindow';
import DocumentList from './components/DocumentList';
import ErrorBoundary from './components/ErrorBoundary';
import AgentChat from './components/AgentChat';
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

export interface ChatSession {
  sessionId: string;
  lastMessage: string;
  createdAt: string;
}

function App() {
  const [sessionId, setSessionId] = useState<string>(() => {
    let id = localStorage.getItem('sessionId');
    if (!id) {
      id = uuidv4();
      localStorage.setItem('sessionId', id);
    }
    return id;
  });

  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem('username'));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem('role'));

  // Auth form states
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);

  // New states for Multi-Document selection
  const [chatMode, setChatMode] = useState<'single' | 'multi'>('single');
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);

  // Tab: 'classic' = existing SSE chat, 'agent' = LangGraph multi-agent
  const [activeTab, setActiveTab] = useState<'classic' | 'agent'>('classic');

  // Sidebar Sub-tab: 'documents' or 'history'
  const [sidebarTab, setSidebarTab] = useState<'documents' | 'history'>('documents');

  // Fetch documents using TanStack Query
  const { data: documents = [], refetch: fetchDocuments } = useQuery<Document[]>({
    queryKey: ['documents', token],
    queryFn: async () => {
      if (!token) return [];
      const response = await fetch(`${API_BASE_URL}/documents`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.status === 401) {
        handleLogout();
        throw new Error('Session expired');
      }
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      return response.json();
    },
    enabled: !!token,
  });

  // Fetch chat sessions
  const { data: sessions = [], refetch: fetchSessions } = useQuery<ChatSession[]>({
    queryKey: ['chatSessions', token],
    queryFn: async () => {
      if (!token) return [];
      const response = await fetch(`${API_BASE_URL}/chat/sessions`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('Failed to fetch sessions');
      return response.json();
    },
    enabled: !!token && sidebarTab === 'history',
  });

  const handleNewChat = () => {
    const newId = uuidv4();
    setSessionId(newId);
    localStorage.setItem('sessionId', newId);
    setSelectedDocument(null);
    setSelectedDocumentIds([]);
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authUsername.trim() || !authPassword.trim()) {
      setAuthError('Please fill in all fields');
      return;
    }
    setAuthError('');
    setAuthLoading(true);

    try {
      const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername, password: authPassword }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Authentication failed');
      }

      const data = await response.json();
      localStorage.setItem('token', data.token);
      localStorage.setItem('username', data.username);
      localStorage.setItem('role', data.role);
      
      setToken(data.token);
      setUsername(data.username);
      setRole(data.role);

      setAuthUsername('');
      setAuthPassword('');
    } catch (err: any) {
      setAuthError(err.message || 'Something went wrong');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    setToken(null);
    setUsername(null);
    setRole(null);
  };

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

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-900 via-indigo-950 to-slate-900 p-6 font-sans">
        <div className="w-full max-w-md bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl text-white">
          <div className="text-center mb-8">
            <span className="text-4xl">🔮</span>
            <h2 className="text-2xl font-bold mt-3 bg-gradient-to-r from-indigo-200 to-white bg-clip-text text-transparent">Smart Doc Chatbot</h2>
            <p className="text-xs text-indigo-200/60 mt-1.5 font-semibold">Enterprise Agentic CRAG Platform</p>
          </div>

          <div className="flex bg-white/5 p-1 rounded-2xl mb-6 border border-white/5">
            <button
              onClick={() => { setAuthMode('login'); setAuthError(''); }}
              className={`flex-1 text-center py-2.5 text-xs font-bold rounded-xl transition-all duration-300 ${
                authMode === 'login'
                  ? 'bg-white text-indigo-950 shadow-md'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setAuthMode('register'); setAuthError(''); }}
              className={`flex-1 text-center py-2.5 text-xs font-bold rounded-xl transition-all duration-300 ${
                authMode === 'register'
                  ? 'bg-white text-indigo-950 shadow-md'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              Create Account
            </button>
          </div>

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-indigo-200/70 mb-1.5">Username</label>
              <input
                type="text"
                value={authUsername}
                onChange={(e) => setAuthUsername(e.target.value)}
                placeholder="Enter username"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-sm font-semibold text-white placeholder-white/30 focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/40 transition duration-200"
                required
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-indigo-200/70 mb-1.5">Password</label>
              <input
                type="password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-sm font-semibold text-white placeholder-white/30 focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/40 transition duration-200"
                required
              />
            </div>

            {authError && (
              <p className="text-rose-400 text-xs font-bold bg-rose-500/10 border border-rose-500/20 px-3.5 py-2.5 rounded-xl">
                ⚠️ {authError}
              </p>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3.5 bg-white text-indigo-950 hover:bg-indigo-50 font-bold text-xs rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center"
            >
              {authLoading ? (
                <span className="w-4 h-4 border-2 border-indigo-950 border-t-transparent rounded-full animate-spin"></span>
              ) : authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 overflow-hidden bg-white border-r border-gray-200 flex flex-col`}>
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <span>📚</span> Smart Doc Chat
          </h1>
          <div className="flex items-center justify-between mt-1">
            <p className="text-xs text-gray-400">User: <span className="font-semibold text-gray-600">{username}</span></p>
            <p className="text-[10px] font-bold text-indigo-600 bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 rounded">
              {role?.replace('ROLE_', '')}
            </p>
          </div>
        </div>

        <div className="p-3">
          <button
            onClick={handleNewChat}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2 mb-3"
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

        {/* Logout Section */}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50 flex items-center justify-between">
          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Session active</p>
          <button
            onClick={handleLogout}
            className="text-xs font-bold text-rose-500 hover:text-rose-700 transition"
          >
            Logout 🚪
          </button>
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
              <p className="text-gray-500 text-sm font-semibold">Select a document in the sidebar to begin</p>
            )}
          </div>
        </div>

        {/* Chat Content */}
        <ErrorBoundary>
          {/* ── Tab switcher ── */}
          <div className="flex border-b border-gray-200 bg-white px-4">
            <button
              onClick={() => setActiveTab('classic')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'classic'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              💬 Classic Chat
            </button>
            <button
              onClick={() => setActiveTab('agent')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'agent'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              🤖 Agent Chat
            </button>
          </div>

          {(() => {
            let agentDocIds: number[];
            if (chatMode === 'multi') {
              agentDocIds = selectedDocumentIds;
            } else if (selectedDocument) {
              agentDocIds = [selectedDocument.id];
            } else {
              agentDocIds = [];
            }
            if (activeTab === 'agent' && token) {
              return (
                <AgentChat
                  token={token}
                  sessionId={sessionId}
                  documentIds={agentDocIds}
                />
              );
            }
            if (activeTab === 'agent') {
              return (
                <div className="flex-1 flex items-center justify-center text-gray-400 bg-gray-50">
                  <p className="text-sm">Please log in to use Agent Chat.</p>
                </div>
              );
            }
            return null;
          })()}
          {activeTab === 'classic' && chatMode === 'multi' ? (
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
        </ErrorBoundary>
      </div>
    </div>
  );
}

export default App;
