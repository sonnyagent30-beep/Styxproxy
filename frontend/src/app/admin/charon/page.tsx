'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { LearnedFile, LearnContentResponse, LearnRequest } from '@/types';

export default function AdminCharonPage() {
  const [files, setFiles] = useState<LearnedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<LearnContentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Form state
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [filename, setFilename] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  
  // View mode
  const [activeTab, setActiveTab] = useState<'files' | 'write'>('files');

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    setLoading(true);
    const result = await api.getLearnedFiles();
    if (result.error) {
      setError(result.error);
    } else {
      setFiles(result.data?.files || []);
    }
    setLoading(false);
  };

  const loadFileContent = async (filename: string) => {
    const result = await api.getLearnedFileContent(filename);
    if (result.error) {
      setError(result.error);
    } else {
      setSelectedFile(result.data || null);
    }
  };

  const handleDelete = async (filename: string) => {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    
    const result = await api.deleteLearnedFile(filename);
    if (result.error) {
      setError(result.error);
    } else {
      await loadFiles();
      setSelectedFile(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) {
      setSaveMessage('Title and content are required');
      return;
    }
    
    setSaving(true);
    setSaveMessage('');
    
    const data: LearnRequest = {
      title: title.trim(),
      content: content.trim(),
      filename: filename.trim() || undefined,
    };
    
    const result = await api.learnContent(data);
    if (result.error) {
      setSaveMessage(result.error);
    } else {
      setSaveMessage(`Saved to ${result.data?.filepath}`);
      setTitle('');
      setContent('');
      setFilename('');
      await loadFiles();
      setActiveTab('files');
    }
    setSaving(false);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2">
                Charon <span className="gradient-text">Knowledge</span>
              </h1>
              <p className="text-[var(--muted)]">Manage Charon's learned knowledge base</p>
            </div>
            <a
              href="/admin"
              className="px-4 py-2 rounded-lg bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              ← Back to Admin
            </a>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
            {error}
            <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-white">
              ✕
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex space-x-2 mb-6">
          <button
            onClick={() => setActiveTab('files')}
            className={`px-6 py-2 rounded-full font-medium transition-all ${
              activeTab === 'files'
                ? 'bg-[var(--primary)] text-black'
                : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
            }`}
          >
            Learned Files
          </button>
          <button
            onClick={() => setActiveTab('write')}
            className={`px-6 py-2 rounded-full font-medium transition-all ${
              activeTab === 'write'
                ? 'bg-[var(--primary)] text-black'
                : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
            }`}
          >
            Write New
          </button>
        </div>

        {/* Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: File List */}
          <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
            <h2 className="text-xl font-semibold mb-4">Learned Files</h2>
            
            {loading ? (
              <div className="text-center py-8 text-[var(--muted)]">Loading...</div>
            ) : files.length === 0 ? (
              <div className="text-center py-8 text-[var(--muted)]">
                No learned files yet. Write some content!
              </div>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.name}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      selectedFile?.name === file.name
                        ? 'bg-[var(--primary)]/10 border-[var(--primary)]'
                        : 'bg-[var(--card-hover)] border-transparent hover:border-[var(--border)]'
                    }`}
                    onClick={() => loadFileContent(file.name)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{file.name}</p>
                        <p className="text-sm text-[var(--muted)]">
                          {formatSize(file.size)} • {formatDate(file.modified_at)}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(file.name);
                        }}
                        className="p-2 text-[var(--muted)] hover:text-red-400 transition-colors"
                        title="Delete file"
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Content Preview or Write Form */}
          <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
            {activeTab === 'files' ? (
              <>
                <h2 className="text-xl font-semibold mb-4">Content Preview</h2>
                {selectedFile ? (
                  <div className="prose prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap text-sm bg-[var(--card-hover)] p-4 rounded-lg overflow-auto max-h-[500px]">
                      {selectedFile.content}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-8 text-[var(--muted)]">
                    Select a file to preview its content
                  </div>
                )}
              </>
            ) : (
              <>
                <h2 className="text-xl font-semibold mb-4">Write New Content</h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Title</label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g., Refund Policy"
                      className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Custom Filename <span className="text-[var(--muted)]">(optional)</span>
                    </label>
                    <input
                      type="text"
                      value={filename}
                      onChange={(e) => setFilename(e.target.value)}
                      placeholder="e.g., refund-policy (will add .md)"
                      className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                    />
                    <p className="text-xs text-[var(--muted)] mt-1">
                      If not provided, filename will be generated from title + timestamp
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Content (Markdown)</label>
                    <textarea
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      placeholder="Write your knowledge content here... Use Markdown for formatting."
                      className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none min-h-[300px]"
                      required
                    />
                  </div>
                  
                  <button
                    type="submit"
                    disabled={saving}
                    className="w-full py-3 rounded-lg bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save to Knowledge Base'}
                  </button>
                  
                  {saveMessage && (
                    <p className={`text-center text-sm ${saveMessage.includes('Saved') ? 'text-green-400' : 'text-red-400'}`}>
                      {saveMessage}
                    </p>
                  )}
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
