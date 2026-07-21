'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { ContactSubmission } from '@/types';

type StatusFilter = 'all' | 'pending' | 'replied' | 'closed';

export default function ContactSubmissionsPage() {
  const [submissions, setSubmissions] = useState<ContactSubmission[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [page, setPage] = useState(1);
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const limit = 20;

  useEffect(() => {
    loadSubmissions();
  }, [statusFilter, page]);

  const loadSubmissions = async () => {
    setLoading(true);
    setError('');

    const status = statusFilter === 'all' ? undefined : statusFilter;
    const result = await api.getContactSubmissions(status, page, limit);

    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setSubmissions(result.data.data);
      setTotal(result.data.total);
    }

    setLoading(false);
  };

  const handleReply = async (id: string) => {
    if (!replyText.trim()) return;

    setSubmitting(true);
    const result = await api.replyContactSubmission(id, replyText);

    if (!result.error) {
      setReplyingTo(null);
      setReplyText('');
      loadSubmissions();
    }

    setSubmitting(false);
  };

  const handleUpdateStatus = async (id: string, newStatus: string) => {
    const result = await api.updateContactSubmission(id, newStatus);
    if (!result.error) {
      loadSubmissions();
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const truncate = (text: string, length: number) => {
    return text.length > length ? text.substring(0, length) + '...' : text;
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400',
      replied: 'bg-green-500/20 text-green-400',
      closed: 'bg-gray-500/20 text-gray-400',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const totalPages = Math.ceil(total / limit);

  const tabs: { label: string; value: StatusFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'Pending', value: 'pending' },
    { label: 'Replied', value: 'replied' },
    { label: 'Closed', value: 'closed' },
  ];

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl lg:text-4xl font-bold">Contact Submissions</h1>
          <span className="px-3 py-1 rounded-full bg-[var(--primary)]/20 text-[var(--primary)] text-sm font-medium">
            {total} total
          </span>
        </div>
        <button
          onClick={loadSubmissions}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity"
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
            onClick={() => {
              setStatusFilter(tab.value);
              setPage(1);
            }}
            className={`px-4 py-2 rounded-xl font-medium whitespace-nowrap transition-colors ${
              statusFilter === tab.value
                ? 'bg-[var(--primary)] text-white'
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
          <button onClick={loadSubmissions} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        {loading ? (
          <div className="p-8">
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse flex gap-4">
                  <div className="h-4 bg-[var(--card-hover)] rounded w-24"></div>
                  <div className="h-4 bg-[var(--card-hover)] rounded w-32"></div>
                  <div className="h-4 bg-[var(--card-hover)] rounded w-48"></div>
                  <div className="h-4 bg-[var(--card-hover)] rounded w-full"></div>
                </div>
              ))}
            </div>
          </div>
        ) : submissions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--card-hover)] flex items-center justify-center">
              <svg className="w-8 h-8 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">No Submissions Found</h3>
            <p className="text-[var(--muted)]">
              {statusFilter === 'all'
                ? 'No contact submissions yet.'
                : `No ${statusFilter} submissions.`}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Date</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Name</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Email</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Message</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((submission) => (
                  <tr key={submission.id} className="border-b border-[var(--border)] hover:bg-[var(--card-hover)]/50">
                    <td className="p-4 text-sm">{formatDate(submission.created_at)}</td>
                    <td className="p-4 font-medium">{submission.name}</td>
                    <td className="p-4 text-sm text-[var(--primary)]">{submission.email}</td>
                    <td className="p-4 text-sm hidden md:table-cell" title={submission.message}>
                      {truncate(submission.message, 100)}
                    </td>
                    <td className="p-4">{getStatusBadge(submission.status)}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        {replyingTo === submission.id ? (
                          <div className="flex flex-col gap-2 w-64">
                            <textarea
                              value={replyText}
                              onChange={(e) => setReplyText(e.target.value)}
                              placeholder="Write your reply..."
                              className="w-full p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-sm resize-none"
                              rows={3}
                              autoFocus
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleReply(submission.id)}
                                disabled={submitting || !replyText.trim()}
                                className="px-3 py-1 rounded-lg bg-green-500 text-white text-sm font-medium hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {submitting ? 'Sending...' : 'Send'}
                              </button>
                              <button
                                onClick={() => {
                                  setReplyingTo(null);
                                  setReplyText('');
                                }}
                                className="px-3 py-1 rounded-lg bg-[var(--card-hover)] text-sm font-medium hover:bg-[var(--border)]"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <button
                              onClick={() => setReplyingTo(submission.id)}
                              className="px-3 py-1 rounded-lg bg-[var(--primary)]/10 text-[var(--primary)] text-sm font-medium hover:bg-[var(--primary)]/20"
                            >
                              Reply
                            </button>
                            {submission.status === 'pending' || submission.status === 'replied' ? (
                              <button
                                onClick={() => handleUpdateStatus(submission.id, 'closed')}
                                className="px-3 py-1 rounded-lg bg-[var(--card-hover)] text-sm font-medium hover:bg-[var(--border)]"
                              >
                                Close
                              </button>
                            ) : (
                              <button
                                onClick={() => handleUpdateStatus(submission.id, 'pending')}
                                className="px-3 py-1 rounded-lg bg-[var(--card-hover)] text-sm font-medium hover:bg-[var(--border)]"
                              >
                                Reopen
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-sm text-[var(--muted)]">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] font-medium hover:bg-[var(--card-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] font-medium hover:bg-[var(--card-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
