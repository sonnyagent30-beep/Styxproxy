'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { AdminStats } from '@/types';

export default function AdminCredentialsPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');

    const result = await api.getAdminStats();
    
    if (result.error) {
      setError(result.error);
    } else {
      setStats(result.data || null);
    }

    setLoading(false);
  };

  // Credentials API is not implemented - show placeholder
  const hasCredentialsApi = false;

  if (loading) {
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
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity"
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
          <button onClick={loadData} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Stats Row */}
      <div className="grid sm:grid-cols-3 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active</p>
          <p className="text-3xl font-bold text-green-400">{stats?.active_credentials ?? 0}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Expired</p>
          <p className="text-3xl font-bold text-gray-400">-</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Revoked</p>
          <p className="text-3xl font-bold text-red-400">-</p>
        </div>
      </div>

      {/* Placeholder when no credentials API */}
      {!hasCredentialsApi && (
        <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--card-hover)] flex items-center justify-center">
            <svg className="w-8 h-8 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold mb-2">Credential Management Coming Soon</h3>
          <p className="text-[var(--muted)] max-w-md mx-auto">
            Connect to your proxy provider API to enable credential management. This will allow you to view, replace, and manage issued proxy credentials directly from this dashboard.
          </p>
          <div className="mt-6 p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] max-w-md mx-auto">
            <p className="text-sm text-[var(--muted)]">
              <span className="font-medium text-[var(--foreground)]">Required:</span> Proxy provider API integration (DataImpulse, Proxy-Seller, etc.)
            </p>
          </div>
        </div>
      )}

      {/* Credentials Table (when API is available) */}
      {hasCredentialsApi && (
        <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Username</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">IP</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Port</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden sm:table-cell">Expires</th>
                  <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[var(--muted)]">
                    No credentials data available
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
