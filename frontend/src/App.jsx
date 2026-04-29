import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import ChatWindow from './components/ChatWindow';
import DocumentList from './components/DocumentList';
import { v4 as uuidv4 } from 'uuid';

function App() {
  const [sessionId] = useState(() => {
    let id = localStorage.getItem('sessionId');
    if (!id) {
      id = uuidv4();
      localStorage.setItem('sessionId', id);
    }
    return id;
  });

  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/documents');
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const handleDocumentUploaded = () => {
    fetchDocuments();
  };

  const handleDocumentDeleted = (id) => {
    setDocuments(documents.filter(doc => doc.id !== id));
    if (selectedDocument?.id === id) {
      setSelectedDocument(null);
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 overflow-hidden bg-white border-r border-gray-200 flex flex-col`}>
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-800">Smart Doc Chat</h1>
          <p className="text-sm text-gray-500 mt-1">Session: {sessionId.slice(0, 8)}...</p>
        </div>

        <DocumentUpload onDocumentUploaded={handleDocumentUploaded} />

        <div className="flex-1 overflow-y-auto">
          <DocumentList
            documents={documents}
            selectedDocument={selectedDocument}
            onSelectDocument={setSelectedDocument}
            onDocumentDeleted={handleDocumentDeleted}
          />
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            {sidebarOpen ? '←' : '→'}
          </button>
          <div className="flex-1 ml-4">
            {selectedDocument && (
              <div>
                <h2 className="text-lg font-semibold text-gray-800">{selectedDocument.fileName}</h2>
                <p className="text-sm text-gray-500">{selectedDocument.chunkCount} chunks</p>
              </div>
            )}
            {!selectedDocument && (
              <p className="text-gray-500">Select a document to start chatting</p>
            )}
          </div>
        </div>

        {/* Chat Content */}
        {selectedDocument ? (
          <ChatWindow sessionId={sessionId} documentId={selectedDocument.id} />
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <p className="text-xl mb-2">📄 No document selected</p>
              <p>Upload or select a document to start chatting</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
