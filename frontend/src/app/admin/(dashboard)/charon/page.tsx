'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import {
  LearnedFile,
  LearnContentResponse,
  LearnRequest,
  UpdateKnowledgeRequest,
  AllKnowledgeFilesResponse,
} from '@/types';

/** Split "intro\n---\nrest" or "intro\n\nrest" into title + body */
function splitTitleBody(raw: string): { title: string; body: string } {
  const h1Match = raw.match(/^#\s+(.+?)[\n\r]/m);
  if (h1Match) {
    const title = h1Match[1].trim();
    const body = raw.slice(h1Match[0].length).trimStart();
    return { title, body };
  }
  return { title: '', body: raw };
}

export default function AdminCharonPage() {
  const [knowledgeFiles, setKnowledgeFiles] = useState<LearnedFile[]>([]);
  const [learnedFiles, setLearnedFiles] = useState<LearnedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<{ name: string; title: string; body: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Edit / create form
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [editingName, setEditingName] = useState(''); // empty = creating new
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const [activeTab, setActiveTab] = useState<'files' | 'write'>('files');

  const loadAll = useCallback(async () => {
    setLoading(true);
    const result = await api.getAllKnowledgeFiles();
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setKnowledgeFiles(result.data.knowledge);
      setLearnedFiles(result.data.learned);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleSelectFile = async (name: string) => {
    const result = await api.getKnowledgeFile(name);
    if (result.error) { setError(result.error); return; }
    const data = result.data!;
    const { title: t, body: b } = splitTitleBody(data.content);
    setTitle(t);
    setContent(b);
    setEditingName(name);
    setSaveMessage('');
    setActiveTab('write');
  };

  const handleNew = () => {
    setTitle('');
    setContent('');
    setEditingName('');
    setSaveMessage('');
    setActiveTab('write');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) {
      setSaveMessage('Title and content are required');
      return;
    }
    setSaving(true);
    setSaveMessage('');

    if (editingName) {
      // Update existing file
      const data: UpdateKnowledgeRequest = { title: title.trim(), content: content.trim() };
      const result = await api.updateKnowledgeFile(editingName, data);
      if (result.error) {
        setSaveMessage(result.error);
      } else {
        setSaveMessage(`Saved — '${editingName}' updated`);
        await loadAll();
      }
    } else {
      // Create new file
      const data: LearnRequest = { title: title.trim(), content: content.trim() };
      const result = await api.learnContent(data);
      if (result.error) {
        setSaveMessage(result.error);
      } else {
        setSaveMessage(`Created — ${result.data?.filepath}`);
        setTitle('');
        setContent('');
        await loadAll();
        setActiveTab('files');
      }
    }
    setSaving(false);
  };

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    const result = await api.deleteLearnedFile(name);
    if (!result.error) {
      if (selectedFile?.name === name) setSelectedFile(null);
      await loadAll();
    }
  };

  const fmtSize = (bytes: number) =>
    bytes < 1024 ? `${bytes} B` :
    bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` :
    `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  const fmtDate = (d: string) => {
    try { return new Date(d).toLocaleDateString(); } catch { return d; }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Charon Knowledge Base</h1>
          <p className="text-sm text-[var(--muted)]">
            Manage files that Charon uses to answer customer questions.
          </p>
        </div>
        <button
          onClick={handleNew}
          className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-sm transition-colors"
        >
          + New File
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {(['files', 'write'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab
                ? 'border-[var(--primary)] text-[var(--primary)]'
                : 'border-transparent text-[var(--muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {tab === 'files' ? 'Knowledge Files' : editingName ? `Edit: ${editingName}` : 'New File'}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* ── Files Tab ─────────────────────────────────────── */}
      {activeTab === 'files' && (
        <div className="space-y-6">
          {loading ? (
            <p className="text-[var(--muted)] text-sm">Loading…</p>
          ) : (
            <>
              {/* Static knowledge files */}
              {knowledgeFiles.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wider mb-3">
                    Built-in Knowledge
                  </h2>
                  <div className="space-y-2">
                    {knowledgeFiles.map(f => (
                      <FileRow
                        key={f.name}
                        file={f}
                        onSelect={() => handleSelectFile(f.name)}
                        onDelete={handleDelete}
                        fmtSize={fmtSize}
                        fmtDate={fmtDate}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Learned / user-added files */}
              {learnedFiles.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wider mb-3">
                    Custom / Learned
                  </h2>
                  <div className="space-y-2">
                    {learnedFiles.map(f => (
                      <FileRow
                        key={f.name}
                        file={f}
                        onSelect={() => handleSelectFile(f.name)}
                        onDelete={handleDelete}
                        fmtSize={fmtSize}
                        fmtDate={fmtDate}
                      />
                    ))}
                  </div>
                </div>
              )}

              {knowledgeFiles.length === 0 && learnedFiles.length === 0 && (
                <p className="text-[var(--muted)] text-sm">No knowledge files found.</p>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Write / Edit Tab ──────────────────────────────── */}
      {activeTab === 'write' && (
        <form onSubmit={handleSubmit} className="space-y-4">
          {editingName && (
            <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <span>Editing:</span>
              <code className="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)]">
                {editingName}
              </code>
              <button
                type="button"
                onClick={() => { setEditingName(''); setTitle(''); setContent(''); setSaveMessage(''); }}
                className="text-xs underline hover:text-[var(--foreground)]"
              >
                Cancel edit
              </button>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. Residential Proxy Plans"
              className="w-full px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--primary)]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Content <span className="text-[var(--muted)] font-normal">(Markdown)</span>
            </label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              placeholder="Write your knowledge base content in Markdown..."
              rows={20}
              className="w-full px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm font-mono focus:outline-none focus:border-[var(--primary)] resize-y"
            />
          </div>

          {saveMessage && (
            <p className={`text-sm ${saveMessage.includes('error') || saveMessage.includes('not') ? 'text-red-400' : 'text-green-400'}`}>
              {saveMessage}
            </p>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 text-black font-semibold rounded-lg text-sm transition-colors"
            >
              {saving ? 'Saving…' : editingName ? 'Save Changes' : 'Create File'}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('files')}
              className="px-4 py-2 border border-[var(--border)] hover:border-[var(--primary)] rounded-lg text-sm transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function FileRow({
  file,
  onSelect,
  onDelete,
  fmtSize,
  fmtDate,
}: {
  file: LearnedFile;
  onSelect: () => void;
  onDelete: (name: string) => void;
  fmtSize: (n: number) => string;
  fmtDate: (d: string) => string;
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] transition-colors group">
      <div className="flex-1 min-w-0 cursor-pointer" onClick={onSelect}>
        <p className="text-sm font-medium truncate">{file.name}</p>
        <p className="text-xs text-[var(--muted)]">
          {fmtSize(file.size)} &middot; {fmtDate(file.modified_at)}
        </p>
      </div>
      <button
        onClick={e => { e.stopPropagation(); onDelete(file.name); }}
        className="opacity-0 group-hover:opacity-100 px-2 py-1 text-xs text-red-400 border border-red-400/30 rounded hover:bg-red-400/10 transition-all"
      >
        Delete
      </button>
    </div>
  );
}
