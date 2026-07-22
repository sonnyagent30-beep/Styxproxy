'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import api from '@/lib/api';
import type { AdminAuditLog, AdminAuditLogResponse } from '@/types';

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
  { value: 'create_admin', label: 'Create Admin' },
  { value: 'update_role', label: 'Update Role' },
  { value: 'lock_admin', label: 'Lock Admin' },
  { value: 'unlock_admin', label: 'Unlock Admin' },
  { value: 'deactivate_admin', label: 'Deactivate Admin' },
  { value: 'update_setting', label: 'Update Setting' },
  { value: 'create_setting', label: 'Create Setting' },
  { value: 'delete_order', label: 'Delete Order' },
  { value: 'refund_order', label: 'Refund Order' },
  { value: 'update_order', label: 'Update Order' },
  { value: 'create_customer', label: 'Create Customer' },
  { value: 'delete_customer', label: 'Delete Customer' },
];

export default function AuditLogPage() {
  const searchParams = useSearchParams();
  const [logs, setLogs] = useState<AdminAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  
  // Filters
  const [actionFilter, setActionFilter] = useState(searchParams.get('action') || '');
  const [emailFilter, setEmailFilter] = useState(searchParams.get('email') || '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '');
  
  const limit = 20;

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError('');
    
    const result = await api.getAuditLogs({
      action: actionFilter || undefined,
      admin_email: emailFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
      limit,
    });

    if (result.error) {
      setError(result.error);
    } else {
      setLogs(result.data?.data || []);
      setTotal(result.data?.pagination?.total_items || 0);
      setTotalPages(result.data?.pagination?.total_pages || 0);
    }
    
    setLoading(false);
  }, [actionFilter, emailFilter, dateFrom, dateTo, page]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadLogs();
  };

  const handleClearFilters = () => {
    setActionFilter('');
    setEmailFilter('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
    loadLogs();
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold mb-2">
          Audit <span className="gradient-text">Log</span>
        </h1>
        <p className="text-[var(--muted)]">All superadmin actions — who did what, when</p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadLogs} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Filters */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Action</label>
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            >
              {ACTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Admin Email</label>
            <input
              type="text"
              value={emailFilter}
              onChange={(e) => setEmailFilter(e.target.value)}
              placeholder="admin@example.com"
              className="w-full px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Date From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Date To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
          
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity"
            >
              Search
            </button>
            <button
              type="button"
              onClick={handleClearFilters}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      </form>

      {/* Results count */}
      <p className="text-sm text-[var(--muted)] mb-4">
        {total > 0 ? `Showing ${logs.length} of ${total} events` : 'No events found'}
      </p>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">When</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Who</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Action</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Resource</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">IP</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border)]">
                    <td className="p-4"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-32"></div></td>
                    <td className="p-4"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-40"></div></td>
                    <td className="p-4"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-24"></div></td>
                    <td className="p-4 hidden md:table-cell"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-32"></div></td>
                    <td className="p-4 hidden lg:table-cell"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-28"></div></td>
                  </tr>
                ))
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <svg className="w-12 h-12 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p className="text-[var(--muted)]">No audit events yet</p>
                    </div>
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors">
                    <td className="p-4 text-sm">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="p-4 text-sm">
                      {log.admin_email || <span className="text-[var(--muted)]">—</span>}
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/20">
                        {log.action}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-[var(--muted)] hidden md:table-cell">
                      {log.resource || <span className="text-[var(--muted)]">—</span>}
                    </td>
                    <td className="p-4 text-sm text-[var(--muted)] hidden lg:table-cell">
                      {log.ip_address || <span className="text-[var(--muted)]">—</span>}
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
    </div>
  );
}
