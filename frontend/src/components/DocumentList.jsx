import React from 'react';
import PropTypes from 'prop-types';
import { formatDistanceToNow } from 'date-fns';

function DocumentList({ documents, selectedDocument, onSelectDocument, onDocumentDeleted }) {
  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (globalThis.confirm('Are you sure you want to delete this document?')) {
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
              className={`flex items-stretch rounded-lg overflow-hidden transition ${
                selectedDocument?.id === doc.id
                  ? 'bg-blue-100 border-l-4 border-blue-500'
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
            >
              <button
                type="button"
                onClick={() => onSelectDocument(doc)}
                className="flex-1 p-3 text-left min-w-0"
                aria-label={`Select ${doc.fileName}`}
              >
                <p className="text-sm font-medium text-gray-800 truncate">{doc.fileName}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {doc.chunkCount} chunks • {(doc.fileSize / 1024).toFixed(1)}KB
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {formatDistanceToNow(new Date(doc.createdAt), { addSuffix: true })}
                </p>
              </button>
              <button
                type="button"
                onClick={(e) => handleDelete(doc.id, e)}
                className="px-3 text-red-500 hover:bg-red-50 transition flex-shrink-0"
                title="Delete"
                aria-label={`Delete ${doc.fileName}`}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default DocumentList;

DocumentList.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number,
    fileName: PropTypes.string,
    fileSize: PropTypes.number,
    chunkCount: PropTypes.number,
    createdAt: PropTypes.string,
  })).isRequired,
  selectedDocument: PropTypes.shape({ id: PropTypes.number }),
  onSelectDocument: PropTypes.func.isRequired,
  onDocumentDeleted: PropTypes.func.isRequired,
};

DocumentList.defaultProps = {
  selectedDocument: null,
};
