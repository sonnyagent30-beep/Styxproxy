'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import type { SupportThread } from '@/types';

type StatusFilter = 'all' | 'open' | 'closed';

export default function SupportInboxPage() {
  const [threads, setThreads] = useState<SupportThread[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const loadThreads = async () => {
    setLoading(true);
    setError('');
    const result = await api.getSupportThreads(statusFilter === 'all' ? undefined : statusFilter);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setThreads(result.data.threads || []);
      setTotal(result.data.pagination?.total || result.data.pagination?.total_items || 0);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadThreads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => loadThreads(), 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
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

  const tabs: { label: string; value: StatusFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'Open', value: 'open' },
    { label: 'Closed', value: 'closed' },
  ];

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/15 flex items-center justify-center">
            <svg className="w-6 h-6 text-[var(--primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold">Support Inbox</h1>
            <p className="text-[var(--muted)] text-sm mt-1">Customer conversations from support@styxproxy.com</p>
          </div>
          {total > 0 && (
            <span className="px-3 py-1 rounded-full bg-[var(--primary)]/20 text-[var(--primary)] text-sm font-medium">
              {total} total
            </span>
          )}
        </div>
        <button
          onClick={loadThreads}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Status Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-4 py-2 rounded-xl font-medium whitespace-nowrap transition-colors ${
              statusFilter === tab.value
                ? 'bg-[var(--primary)] text-black'
                : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadThreads} className="ml-4 text-red-300 hover:text-white">Retry</button>
        </div>
      )}

      {/* Thread List */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        {loading ? (
          <div className="p-8 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="animate-pulse flex gap-4 items-center">
                <div className="h-10 w-10 rounded-full bg-[var(--card-hover)]" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-[var(--card-hover)] rounded w-1/3" />
                  <div className="h-3 bg-[var(--card-hover)] rounded w-1/2" />
                </div>
                <div className="h-3 bg-[var(--card-hover)] rounded w-16" />
              </div>
            ))}
          </div>
        ) : threads.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[var(--card-hover)] flex items-center justify-center">
              <svg className="w-8 h-8 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-1">No support threads yet</h3>
            <p className="text-[var(--muted)] text-sm">When customers email support@styxproxy.com, they'll appear here.</p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {threads.map((thread) => (
              <Link
                key={thread.id}
                href={`/admin/support/${thread.id}`}
                className="block p-5 hover:bg-[var(--card-hover)] transition-colors group relative"
              >
                {/* Green left border on hover */}
                <span className="absolute left-0 top-0 bottom-0 w-1 bg-[var(--primary)] opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--primary)]/30 to-[var(--primary)]/10 flex items-center justify-center text-sm font-bold flex-shrink-0">
                    {(thread.customer_name || thread.customer_email || '?').charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-semibold truncate">{thread.customer_name || thread.customer_email}</span>
                      <span className="text-[var(--muted)] text-sm truncate">{thread.customer_email}</span>
                      {statusPill(thread.status)}
                    </div>
                    <div className="text-[var(--foreground)] font-medium truncate mb-1">{thread.subject}</div>
                    <div className="text-[var(--muted)] text-sm truncate">
                      {thread.resend_last_message_id ? 'Last reply sent · ' : ''}
                      Started {formatTimeAgo(thread.created_at)}
                    </div>
                  </div>
                  <div className="text-xs text-[var(--muted)] flex-shrink-0 self-start">
                    {formatTimeAgo(thread.last_message_at)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}