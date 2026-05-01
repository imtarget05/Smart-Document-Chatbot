import React, { useState } from 'react';
import PropTypes from 'prop-types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';

function DocumentUpload({ onDocumentUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'application/msword', 
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         'text/plain'];
    if (!allowedTypes.includes(file.type)) {
      setError('Only PDF, Word, and TXT files are supported');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        onDocumentUploaded();
        e.target.value = '';
      } else {
        setError(data.message || 'Upload failed');
      }
    } catch (err) {
      setError(err.message || 'Error uploading document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-4 border-b border-gray-200">
      <label className="block">
        <input
          type="file"
          onChange={handleFileChange}
          disabled={uploading}
          className="hidden"
          accept=".pdf,.docx,.doc,.txt"
        />
        <span className="block w-full bg-blue-500 hover:bg-blue-600 text-white text-center py-2 px-4 rounded-lg cursor-pointer transition font-medium">
          {uploading ? 'Uploading...' : '+ Upload Document'}
        </span>
      </label>
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  );
}

export default DocumentUpload;

DocumentUpload.propTypes = {
  onDocumentUploaded: PropTypes.func.isRequired,
};
