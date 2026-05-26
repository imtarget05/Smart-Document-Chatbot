import React, { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8080/api';

interface DocumentUploadProps {
  onDocumentUploaded: () => void;
}

function DocumentUpload({ onDocumentUploaded }: DocumentUploadProps) {
  const [error, setError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload request failed with status ' + response.status);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.message || 'Upload failed');
      }

      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      onDocumentUploaded();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    onError: (err: any) => {
      setError(err.message || 'Error uploading document');
    }
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
    ];
    if (!allowedTypes.includes(file.type)) {
      setError('Only PDF, Word, and TXT files are supported');
      return;
    }

    setError('');
    uploadMutation.mutate(file);
  };

  return (
    <div className="p-4 border-b border-gray-200">
      <label className="block">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          disabled={uploadMutation.isPending}
          className="hidden"
          accept=".pdf,.docx,.doc,.txt"
        />
        <span className={`block w-full text-center py-2 px-4 rounded-lg cursor-pointer transition font-medium text-white shadow-md ${
          uploadMutation.isPending
            ? 'bg-blue-400 cursor-not-allowed'
            : 'bg-blue-500 hover:bg-blue-600 hover:shadow-lg'
        }`}>
          {uploadMutation.isPending ? 'Uploading & Parsing...' : '+ Upload Document'}
        </span>
      </label>
      {error && <p className="text-red-500 text-sm mt-2 font-medium">{error}</p>}
    </div>
  );
}

export default DocumentUpload;
