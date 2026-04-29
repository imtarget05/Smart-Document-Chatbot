import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { viVN } from 'date-fns/locale';

function DocumentList({ documents, selectedDocument, onSelectDocument, onDocumentDeleted }) {
  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await fetch(`http://localhost:8080/api/documents/${id}`, {
          method: 'DELETE',
        });
        onDocumentDeleted(id);
      } catch (error) {
        console.error('Error deleting document:', error);
      }
    }
  };

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase">Documents</h3>
      <div className="space-y-2">
        {documents.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No documents yet</p>
        ) : (
          documents.map(doc => (
            <div
              key={doc.id}
              onClick={() => onSelectDocument(doc)}
              className={`p-3 rounded-lg cursor-pointer transition ${
                selectedDocument?.id === doc.id
                  ? 'bg-blue-100 border-l-4 border-blue-500'
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{doc.fileName}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {doc.chunkCount} chunks • {(doc.fileSize / 1024).toFixed(1)}KB
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {formatDistanceToNow(new Date(doc.createdAt), { addSuffix: true })}
                  </p>
                </div>
                <button
                  onClick={(e) => handleDelete(doc.id, e)}
                  className="ml-2 p-1 text-red-500 hover:bg-red-50 rounded transition"
                  title="Delete"
                >
                  ×
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default DocumentList;
