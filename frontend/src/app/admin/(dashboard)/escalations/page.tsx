'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { CharonEscalation } from '@/types';

export default function AdminEscalationsPage() {
  const [escalations, setEscalations] = useState<CharonEscalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedEscalation, setSelectedEscalation] = useState<CharonEscalation | null>(null);
  const [replyText, setReplyText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [replySent, setReplySent] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');

    const result = await api.getEscalations(page, limit, statusFilter === 'all' ? undefined : statusFilter);

    if (result.error) {
      setError(result.error);
    } else {
      setEscalations(result.data?.escalations || []);
      setTotal(result.data?.total || 0);
    }

    setLoading(false);
  }, [page, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      replied: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      closed: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  const handleReply = async () => {
    if (!selectedEscalation || !replyText.trim()) return;

    setSubmitting(true);
    const result = await api.respondToEscalation(selectedEscalation.id, replyText);

    if (result.error) {
      setError(result.error);
    } else {
      setReplySent(true);
      setReplyText('');
      loadData();
    }
    setSubmitting(false);
  };

  const handleClose = async (escalation: CharonEscalation) => {
    // Close by sending a reply (empty reply marks as closed on backend)
    const result = await api.respondToEscalation(escalation.id, '[CLOSED]');
    if (!result.error) {
      loadData();
    }
  };

  const totalPages = Math.ceil(total / limit);

  if (loading && escalations.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Escalations</h1>
          <p className="text-[var(--muted)]">Manage Charon AI escalations</p>
        </div>
        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-24 mb-2"></div>
              <div className="animate-pulse h-8 bg-[var(--card-hover)] rounded w-16"></div>
            </div>
          ))}
        </div>
        <div className="animate-pulse h-64 bg-[var(--card)] rounded-2xl border border-[var(--border)]"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Escalations</h1>
          <p className="text-[var(--muted)]">Manage Charon AI escalations</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        {['all', 'pending', 'replied', 'closed'].map((status) => (
          <button
            key={status}
            onClick={() => {
              setStatusFilter(status);
              setPage(1);
            }}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              statusFilter === status
                ? 'bg-[var(--primary)] text-white'
                : 'bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)]'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Escalations List */}
      <div className="space-y-4">
        {escalations.length === 0 ? (
          <div className="p-8 text-center bg-[var(--card)] rounded-2xl border border-[var(--border)]">
            <svg className="w-12 h-12 mx-auto text-[var(--muted)] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="text-[var(--muted)]">No escalations found</p>
          </div>
        ) : (
          escalations.map((escalation) => (
            <div
              key={escalation.id}
              className="p-4 bg-[var(--card)] rounded-2xl border border-[var(--border)] hover:border-[var(--primary)]/30 transition-colors cursor-pointer"
              onClick={() => {
                setSelectedEscalation(escalation);
                setReplySent(false);
                setReplyText('');
              }}
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusBadge(escalation.status)}
                    <span className="text-sm text-[var(--muted)]">{formatDate(escalation.created_at)}</span>
                  </div>
                  <p className="font-medium mb-1">
                    {escalation.customer_email || escalation.customer_phone || 'Unknown Customer'}
                  </p>
                  <p className="text-sm text-[var(--muted)] line-clamp-2">
                    {escalation.customer_message}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {escalation.status === 'pending' && (
                    <span className="px-2 py-1 text-xs bg-yellow-500/20 text-yellow-400 rounded-full">
                      Needs Reply
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
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
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--card-hover)] transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--card-hover)] transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedEscalation && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedEscalation(null)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Escalation Details</h2>
                <button onClick={() => setSelectedEscalation(null)} className="p-2 hover:bg-[var(--card-hover)] rounded-lg">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2">
                {getStatusBadge(selectedEscalation.status)}
                <span className="text-sm text-[var(--muted)]">{formatDate(selectedEscalation.created_at)}</span>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Customer Info */}
              <div>
                <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Customer</h3>
                <div className="p-4 rounded-xl bg-[var(--background)]">
                  <p className="font-medium">{selectedEscalation.customer_email || selectedEscalation.customer_phone || 'Unknown'}</p>
                  <p className="text-sm text-[var(--muted)]">Phone: {selectedEscalation.customer_phone || 'N/A'}</p>
                  <p className="text-sm text-[var(--muted)]">Conv ID: {selectedEscalation.conversation_id}</p>
                </div>
              </div>

              {/* Initial Message */}
              <div>
                <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Initial Message</h3>
                <div className="p-4 rounded-xl bg-[var(--background)]">
                  <p className="whitespace-pre-wrap">{selectedEscalation.customer_message}</p>
                </div>
              </div>

              {/* History Summary */}
              {selectedEscalation.history_summary && (
                <div>
                  <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Conversation History</h3>
                  <div className="p-4 rounded-xl bg-[var(--background)]">
                    <p className="text-sm whitespace-pre-wrap">{selectedEscalation.history_summary}</p>
                  </div>
                </div>
              )}

              {/* Previous Reply */}
              {selectedEscalation.admin_notes && (
                <div>
                  <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Your Previous Reply</h3>
                  <div className="p-4 rounded-xl bg-[var(--primary)]/10 border border-[var(--primary)]/30">
                    <p className="whitespace-pre-wrap">{selectedEscalation.admin_notes}</p>
                    <p className="text-xs text-[var(--muted)] mt-2">By: {selectedEscalation.admin_phone || 'Admin'}</p>
                  </div>
                </div>
              )}

              {/* Reply Form */}
              {selectedEscalation.status !== 'closed' && (
                <div>
                  <h3 className="text-sm font-medium text-[var(--muted)] mb-3">
                    {replySent ? 'Reply Sent ✓' : 'Send Reply'}
                  </h3>
                  {replySent ? (
                    <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                      <p className="text-green-400 font-medium">Reply sent successfully!</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder="Type your reply to the customer..."
                        className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                        rows={4}
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={handleReply}
                          disabled={!replyText.trim() || submitting}
                          className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                        >
                          {submitting ? 'Sending...' : 'Send Reply'}
                        </button>
                        {selectedEscalation.status === 'pending' && (
                          <button
                            onClick={() => handleClose(selectedEscalation)}
                            className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
                          >
                            Close
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
