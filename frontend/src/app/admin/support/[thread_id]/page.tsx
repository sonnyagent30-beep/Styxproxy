'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import type { SupportThreadDetail, SupportMessage } from '@/types';

export default function ThreadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const threadId = params?.thread_id as string;

  const [thread, setThread] = useState<SupportThreadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [replyText, setReplyText] = useState('');
  const [sending, setSending] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<SupportMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadThread = async () => {
    if (!threadId) return;
    setLoading(true);
    setError('');
    const result = await api.getSupportThread(threadId);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setThread(result.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadThread();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  // Auto-scroll to bottom when messages load
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thread?.messages, optimisticMessages]);

  const handleSendReply = async () => {
    if (!replyText.trim() || !thread) return;
    setSending(true);

    // Convert plain text to HTML (preserve line breaks)
    const replyHtml = replyText
      .split('\n')
      .map(line => line.trim() ? `<p>${line}</p>` : '<br>')
      .join('');

    // Optimistic UI
    const optimistic: SupportMessage = {
      id: `optimistic-${Date.now()}`,
      thread_id: thread.id,
      direction: 'outbound',
      from_email: 'support@styxproxy.com',
      to_email: thread.customer_email,
      subject: `Re: ${thread.subject}`,
      body_text: replyText,
      body_html: replyHtml,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages([optimistic]);
    const previousText = replyText;
    setReplyText('');

    const result = await api.replySupportThread(thread.id, replyHtml, 'Dannion');
    setSending(false);
    if (result.error) {
      // Revert optimistic
      setOptimisticMessages([]);
      setReplyText(previousText);
      alert(`Failed to send reply: ${result.error}`);
    } else {
      // Reload thread to get the persisted message
      await loadThread();
      setOptimisticMessages([]);
    }
  };

  const handleCloseThread = async () => {
    if (!thread) return;
    if (!confirm('Close this thread? The customer can still reply, but it will be marked closed.')) return;
    setActionLoading(true);
    await api.closeSupportThread(thread.id);
    await loadThread();
    setActionLoading(false);
  };

  const handleReopenThread = async () => {
    if (!thread) return;
    setActionLoading(true);
    await api.reopenSupportThread(thread.id);
    await loadThread();
    setActionLoading(false);
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFullTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const statusPill = (status: string) => {
    const styles: Record<string, string> = {
      open: 'bg-green-500/20 text-green-400 border border-green-500/30',
      replied: 'bg-green-500/20 text-green-400 border border-green-500/30',
      closed: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
    };
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] || styles.open}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${status === 'closed' ? 'bg-gray-400' : 'bg-green-400'}`} />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (loading && !thread) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-[var(--card)] rounded w-48" />
          <div className="h-32 bg-[var(--card)] rounded-2xl" />
          <div className="h-64 bg-[var(--card)] rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error && !thread) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadThread} className="ml-4 underline">Retry</button>
        </div>
      </div>
    );
  }

  if (!thread) return null;

  const allMessages = [...(thread.messages || []), ...optimisticMessages];

  return (
    <div className="max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-[var(--muted)] mb-4">
        <Link href="/admin/support" className="hover:text-[var(--foreground)] transition-colors">
          ← Support Inbox
        </Link>
      </div>

      {/* Header card */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] p-6 mb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[var(--primary)]/30 to-[var(--primary)]/10 flex items-center justify-center text-xl font-bold">
              {(thread.customer_name || thread.customer_email || '?').charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold mb-1">{thread.subject}</h1>
              <div className="flex items-center gap-2 flex-wrap text-sm">
                <span className="text-[var(--foreground)] font-medium">
                  {thread.customer_name || 'Unknown'}
                </span>
                <a
                  href={`mailto:${thread.customer_email}`}
                  className="text-[var(--primary)] hover:underline"
                >
                  {thread.customer_email}
                </a>
                {statusPill(thread.status)}
              </div>
              <div className="text-xs text-[var(--muted)] mt-1">
                Opened {formatFullTime(thread.created_at)}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            {thread.status === 'closed' ? (
              <button
                onClick={handleReopenThread}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl bg-[var(--primary)]/20 text-[var(--primary)] font-medium hover:bg-[var(--primary)]/30 transition-colors disabled:opacity-50"
              >
                Reopen Thread
              </button>
            ) : (
              <button
                onClick={handleCloseThread}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl bg-amber-500/20 text-amber-400 font-medium hover:bg-amber-500/30 transition-colors disabled:opacity-50"
              >
                Close Thread
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Conversation */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] p-6 mb-6 min-h-[400px] max-h-[600px] overflow-y-auto">
        {allMessages.length === 0 ? (
          <div className="text-center py-12 text-[var(--muted)]">
            No messages in this thread yet.
          </div>
        ) : (
          <div className="space-y-4">
            {allMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] ${msg.direction === 'outbound' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                  <div className="flex items-center gap-2 text-xs text-[var(--muted)] px-2">
                    {msg.direction === 'outbound' ? (
                      <>
                        <span className="text-[var(--primary)] font-medium">Dannion (Styxproxy Support)</span>
                        <span>→ {msg.to_email}</span>
                      </>
                    ) : (
                      <>
                        <span>{msg.from_email}</span>
                      </>
                    )}
                    <span>·</span>
                    <span>{formatTime(msg.created_at)}</span>
                  </div>
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      msg.direction === 'outbound'
                        ? 'bg-[var(--primary)]/10 border border-[var(--primary)]/30 text-[var(--foreground)]'
                        : 'bg-[var(--card-hover)] border border-[var(--border)] text-[var(--foreground)]'
                    }`}
                  >
                    {msg.body_html ? (
                      <div
                        className="prose prose-invert prose-sm max-w-none [&_p]:my-2"
                        dangerouslySetInnerHTML={{ __html: msg.body_html }}
                      />
                    ) : (
                      <div className="whitespace-pre-wrap text-sm">{msg.body_text}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Reply form */}
      {thread.status !== 'closed' ? (
        <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] p-6">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-medium text-[var(--muted)]">
              Reply to <span className="text-[var(--foreground)]">{thread.customer_email}</span>
            </label>
            <div className="text-xs text-[var(--muted)]">
              From: <span className="text-[var(--primary)]">support@styxproxy.com</span> (branded)
            </div>
          </div>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Type your reply..."
            rows={6}
            disabled={sending}
            className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20 resize-y disabled:opacity-50"
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                handleSendReply();
              }
            }}
          />
          <div className="flex items-center justify-between mt-3">
            <div className="text-xs text-[var(--muted)]">
              ⌘/Ctrl + Enter to send · Customer will see this in the Styxproxy branded template
            </div>
            <button
              onClick={handleSendReply}
              disabled={sending || !replyText.trim()}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Sending...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  Send Reply
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] p-8 text-center">
          <div className="text-[var(--muted)] mb-2">🔒 This thread is closed</div>
          <p className="text-sm text-[var(--muted)]">Reopen the thread to send a reply.</p>
        </div>
      )}
    </div>
  );
}