import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import api from '../api/axios';

export function Uploads() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [documents, setDocuments] = useState<string[]>([]);

  const fetchDocuments = async () => {
    try {
      const response = await api.get('/uploads/documents');
      if (response.data && response.data.documents) {
        setDocuments(response.data.documents);
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  React.useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUploadStatus('idle');
      setMessage('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setUploadStatus('idle');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/uploads/document', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.status === 200) {
        setUploadStatus('success');
        setMessage(response.data.message || 'File uploaded successfully!');
        setFile(null);
        fetchDocuments();
      }
    } catch (error: any) {
      setUploadStatus('error');
      setMessage(error.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto h-full overflow-y-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Knowledge Base Uploads</h1>
        <p className="text-slate-400">Upload documents to expand the AI's knowledge base. Supported formats: PDF, DOCX, XLSX, CSV, TXT.</p>
      </div>

      <div className="bg-slate-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
        <div className="border-2 border-dashed border-slate-600 rounded-xl p-12 text-center hover:border-blue-500 transition-colors bg-slate-900/30">
          <Upload className="w-16 h-16 text-blue-400 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">Drag and drop your file here</h3>
          <p className="text-slate-400 mb-6">or click to select a file from your computer</p>
          
          <input
            type="file"
            id="file-upload"
            className="hidden"
            onChange={handleFileChange}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
          />
          <label
            htmlFor="file-upload"
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium cursor-pointer inline-flex items-center gap-2 transition-colors"
          >
            <FileText className="w-5 h-5" />
            Select File
          </label>
        </div>

        {file && (
          <div className="mt-8 bg-slate-900/50 rounded-lg p-4 flex items-center justify-between border border-slate-700">
            <div className="flex items-center gap-4">
              <div className="bg-blue-500/20 p-3 rounded-lg">
                <FileText className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-white font-medium">{file.name}</p>
                <p className="text-slate-400 text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            </div>
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Upload Now'}
            </button>
          </div>
        )}

        {uploadStatus === 'success' && (
          <div className="mt-6 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 flex items-center gap-3 text-emerald-400">
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
            <p>{message}</p>
          </div>
        )}

        {uploadStatus === 'error' && (
          <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p>{message}</p>
          </div>
        )}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-bold text-white mb-4">Uploaded Files</h2>
        {documents.length === 0 ? (
          <div className="text-slate-400 bg-slate-800/30 border border-white/5 rounded-xl p-6 text-center">
            No files have been uploaded yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {documents.map((doc, idx) => (
              <div key={idx} className="bg-slate-800/50 backdrop-blur-sm border border-white/10 rounded-xl p-4 flex items-center gap-3 hover:bg-slate-800/80 transition-colors">
                <div className="bg-blue-500/10 p-2 rounded-lg">
                  <FileText className="w-5 h-5 text-blue-400" />
                </div>
                <p className="text-white font-medium truncate" title={doc}>{doc}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
