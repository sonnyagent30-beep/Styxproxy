'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { AdminStats, CredentialDetail } from '@/types';

export default function AdminCredentialsPage() {
  const [credentials, setCredentials] = useState<CredentialDetail[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCredential, setSelectedCredential] = useState<CredentialDetail | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showRotateModal, setShowRotateModal] = useState(false);
  const [rotateCredential, setRotateCredential] = useState<CredentialDetail | null>(null);
  const [rotateReason, setRotateReason] = useState('');
  const limit = 20;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');

    const filters: { status?: string } = {};
    if (statusFilter !== 'all') filters.status = statusFilter;

    const [statsResult, credsResult] = await Promise.all([
      api.getAdminStats(),
      api.getCredentials(page, limit, filters),
    ]);

    if (statsResult.error) {
      setError(statsResult.error);
    } else {
      setStats(statsResult.data || null);
    }

    if (credsResult.error) {
      setError(credsResult.error);
    } else {
      const creds = credsResult.data?.data || [];
      setCredentials(searchQuery 
        ? creds.filter(c => 
            c.styxproxy_username.toLowerCase().includes(searchQuery.toLowerCase()) ||
            c.customer_phone?.includes(searchQuery)
          )
        : creds
      );
      setTotal(credsResult.data?.pagination.total_items || 0);
      setTotalPages(credsResult.data?.pagination.total_pages || 0);
    }

    setLoading(false);
  }, [page, statusFilter, searchQuery]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      active: 'bg-green-500/20 text-green-400 border-green-500/30',
      expired: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
      revoked: 'bg-red-500/20 text-red-400 border-red-500/30',
      rotated: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      suspended: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.active}`}>
        {status}
      </span>
    );
  };

  const handleRotate = async () => {
    if (!rotateCredential || !rotateReason.trim()) return;
    
    const result = await api.rotateCredential(rotateCredential.id, rotateReason);
    
    if (result.error) {
      setError(result.error);
    } else {
      setShowRotateModal(false);
      setRotateCredential(null);
      setRotateReason('');
      loadData();
      // Refresh selected credential if it's the one rotated
      if (selectedCredential?.id === rotateCredential.id) {
        const updated = await api.getCredentialDetail(rotateCredential.id);
        if (updated.data) {
          setSelectedCredential(updated.data);
        }
      }
    }
  };

  const handleUpdateStatus = async (credentialId: number, newStatus: string) => {
    const result = await api.updateCredential(credentialId, { status: newStatus });
    
    if (result.error) {
      setError(result.error);
    } else {
      loadData();
      if (selectedCredential?.id === credentialId) {
        setSelectedCredential({ ...selectedCredential, status: newStatus });
      }
    }
  };

  const statsData = {
    active: credentials.filter(c => c.status === 'active').length,
    expired: credentials.filter(c => c.status === 'expired').length,
    revoked: credentials.filter(c => c.status === 'revoked' || c.status === 'rotated').length,
  };

  if (loading && credentials.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Credentials</h1>
          <p className="text-[var(--muted)]">Manage issued proxy credentials</p>
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
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Credentials</h1>
          <p className="text-[var(--muted)]">Manage issued proxy credentials</p>
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

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by username or customer phone..."
            className="w-full px-4 py-3 pl-12 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
          />
          <svg className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid sm:grid-cols-3 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active</p>
          <p className="text-3xl font-bold text-green-400">{statsData.active}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Expired</p>
          <p className="text-3xl font-bold text-gray-400">{statsData.expired}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Revoked/Rotated</p>
          <p className="text-3xl font-bold text-red-400">{statsData.revoked}</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="revoked">Revoked</option>
          <option value="rotated">Rotated</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Username</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Provider</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Proxy</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Customer</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden sm:table-cell">Rotations</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {credentials.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[var(--muted)]">
                    No credentials found
                  </td>
                </tr>
              ) : (
                credentials.map((cred) => (
                  <tr
                    key={cred.id}
                    className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] cursor-pointer transition-colors"
                    onClick={() => setSelectedCredential(cred)}
                  >
                    <td className="p-4">
                      <span className="font-mono text-sm">{cred.styxproxy_username}</span>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <span className="text-sm">{cred.provider_name || 'N/A'}</span>
                    </td>
                    <td className="p-4 hidden lg:table-cell">
                      <span className="font-mono text-sm">
                        {cred.upstream_proxy_ip}:{cred.upstream_proxy_port}
                      </span>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <span className="text-sm">{cred.customer_phone || 'N/A'}</span>
                    </td>
                    <td className="p-4">{getStatusBadge(cred.status)}</td>
                    <td className="p-4 hidden sm:table-cell">
                      <span className="text-sm">{cred.rotation_count}</span>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCredential(cred);
                        }}
                        className="p-2 hover:bg-[var(--card-hover)] rounded-lg transition-colors"
                        title="View details"
                      >
                        <svg className="w-5 h-5 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
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

      {/* Credential Detail Modal */}
      {selectedCredential && (
        <CredentialDetailModal
          credential={selectedCredential}
          onClose={() => setSelectedCredential(null)}
          onRotate={(cred) => {
            setRotateCredential(cred);
            setShowRotateModal(true);
          }}
          onUpdateStatus={handleUpdateStatus}
          formatDate={formatDate}
          getStatusBadge={getStatusBadge}
        />
      )}

      {/* Rotate Modal */}
      {showRotateModal && rotateCredential && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowRotateModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Rotate Credential</h2>
              <p className="text-sm text-[var(--muted)]">Username: {rotateCredential.styxproxy_username}</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="p-4 rounded-xl bg-orange-500/10 border border-orange-500/20">
                <p className="text-orange-400 font-medium">Warning: This action cannot be undone</p>
                <p className="text-sm text-[var(--muted)]">The current credential will be marked as rotated and a new one will be created.</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Reason for Rotation</label>
                <textarea
                  value={rotateReason}
                  onChange={(e) => setRotateReason(e.target.value)}
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  rows={3}
                  placeholder="Enter reason for rotation..."
                  required
                />
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowRotateModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRotate}
                disabled={!rotateReason.trim()}
                className="flex-1 px-4 py-2 rounded-xl bg-orange-500 text-white font-medium hover:bg-orange-600 transition-colors disabled:opacity-50"
              >
                Rotate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Credential Detail Modal Component
function CredentialDetailModal({
  credential,
  onClose,
  onRotate,
  onUpdateStatus,
  formatDate,
  getStatusBadge,
}: {
  credential: CredentialDetail;
  onClose: () => void;
  onRotate: (cred: CredentialDetail) => void;
  onUpdateStatus: (id: number, status: string) => void;
  formatDate: (dateStr: string) => string;
  getStatusBadge: (status: string) => React.ReactNode;
}) {
  const [showPasswords, setShowPasswords] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const proxyString = credential.provider_username 
    ? `${credential.protocol}://${credential.provider_username}:${credential.provider_password || 'password'}@${credential.upstream_proxy_ip}:${credential.upstream_proxy_port}`
    : null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[var(--border)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Credential Details</h2>
            <button onClick={onClose} className="p-2 hover:bg-[var(--card-hover)] rounded-lg">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        <div className="p-6 space-y-6">
          {/* Basic Info */}
          <div>
            <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Basic Information</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">ID</span>
                <span className="font-mono text-sm">{credential.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Bun Username</span>
                <span className="font-mono">{credential.styxproxy_username}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Provider</span>
                <span>{credential.provider_name || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Customer</span>
                <span>{credential.customer_phone || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Order ID</span>
                <span className="font-mono text-sm">{credential.order_id || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Pool Type</span>
                <span>{credential.pool_type}</span>
              </div>
            </div>
          </div>

          {/* Proxy Info */}
          <div>
            <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Proxy Information</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Protocol</span>
                <span className="font-mono uppercase">{credential.protocol}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Proxy IP</span>
                <span className="font-mono">{credential.upstream_proxy_ip}:{credential.upstream_proxy_port}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Status</span>
                {getStatusBadge(credential.status)}
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Created</span>
                <span>{formatDate(credential.created_at)}</span>
              </div>
              {credential.expires_at && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Expires</span>
                  <span>{formatDate(credential.expires_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Usage Stats */}
          <div>
            <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Usage Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Data Used</span>
                <span>{credential.gb_used.toFixed(2)} GB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Rotations</span>
                <span>{credential.rotation_count}</span>
              </div>
              {credential.last_used_at && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Last Used</span>
                  <span>{formatDate(credential.last_used_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Proxy Credentials - REVEAL ON CLICK */}
          <div>
            <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Proxy Credentials</h3>
            <div className="p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)]">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium">Authentication Details</span>
                <button
                  onClick={() => setShowPasswords(!showPasswords)}
                  className="text-xs text-[var(--primary)] hover:underline flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  {showPasswords ? 'Hide' : 'Reveal'}
                </button>
              </div>
              
              {showPasswords ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-[var(--muted)]">Provider Username</span>
                    <div className="flex items-center gap-2">
                      <code className="px-2 py-1 rounded bg-[var(--background)] text-sm">
                        {credential.provider_username || 'N/A'}
                      </code>
                      {credential.provider_username && (
                        <button
                          onClick={() => copyToClipboard(credential.provider_username!)}
                          className="p-1 hover:bg-[var(--card)] rounded"
                          title="Copy"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[var(--muted)]">Provider Password</span>
                    <code className="px-2 py-1 rounded bg-[var(--background)] text-sm">
                      {credential.provider_password || 'N/A'}
                    </code>
                  </div>
                  
                  {/* Full Proxy String */}
                  {proxyString && (
                    <div className="mt-4 pt-4 border-t border-[var(--border)]">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-[var(--muted)]">Full Proxy String</span>
                        <button
                          onClick={() => copyToClipboard(proxyString)}
                          className="text-xs text-[var(--primary)] hover:underline flex items-center gap-1"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          Copy
                        </button>
                      </div>
                      <code className="block p-3 rounded bg-[var(--background)] text-sm break-all">
                        {proxyString}
                      </code>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-[var(--muted)] text-center py-4">
                  Click "Reveal" to show proxy credentials
                </p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-4 border-t border-[var(--border)]">
            {credential.status === 'active' && (
              <>
                <button
                  onClick={() => onRotate(credential)}
                  className="px-4 py-2 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30 hover:bg-orange-500/30 transition-colors"
                >
                  Rotate Proxy
                </button>
                <button
                  onClick={() => onUpdateStatus(credential.id, 'suspended')}
                  className="px-4 py-2 rounded-xl bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 hover:bg-yellow-500/30 transition-colors"
                >
                  Suspend
                </button>
                <button
                  onClick={() => onUpdateStatus(credential.id, 'revoked')}
                  className="px-4 py-2 rounded-xl bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
                >
                  Revoke
                </button>
              </>
            )}
            {(credential.status === 'suspended' || credential.status === 'revoked') && (
              <button
                onClick={() => onUpdateStatus(credential.id, 'active')}
                className="px-4 py-2 rounded-xl bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-colors"
              >
                Reactivate
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
