'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { Customer, AdminStats, PaginatedResponse } from '@/types';

export default function AdminCustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [blockingId, setBlockingId] = useState<string | null>(null);
  const limit = 20;

  useEffect(() => {
    loadData();
  }, [page]);

  const loadData = async () => {
    setLoading(true);
    setError('');

    const [statsResult, customersResult] = await Promise.all([
      api.getAdminStats(),
      api.getCustomers(page, limit),
    ]);

    if (statsResult.error) {
      setError(statsResult.error);
    } else {
      setStats(statsResult.data || null);
    }

    if (customersResult.error) {
      setError(customersResult.error);
    } else {
      setCustomers(customersResult.data?.data || []);
      setTotal(customersResult.data?.pagination.total_items || 0);
    }

    setLoading(false);
  };

  const handleBlockCustomer = async (customerId: string, blocked: boolean) => {
    const reason = blocked ? 'Blocked by admin' : 'Unblocked by admin';
    setBlockingId(customerId);
    
    const result = await api.blockCustomer(customerId, reason);
    
    if (result.error) {
      setError(result.error);
    } else {
      // Refresh the list
      loadData();
    }
    
    setBlockingId(null);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const totalPages = Math.ceil(total / limit);

  const filteredCustomers = searchQuery
    ? customers.filter(c => 
        c.phone.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : customers;

  if (loading && customers.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Customers</h1>
          <p className="text-[var(--muted)]">Manage your customer base</p>
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
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Customers</h1>
          <p className="text-[var(--muted)]">Manage your customer base</p>
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
          <p className="text-[var(--muted)] text-sm mb-1">Total Customers</p>
          <p className="text-3xl font-bold">{total}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active</p>
          <p className="text-3xl font-bold text-green-400">{customers.filter(c => !c.blocked).length}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Blocked</p>
          <p className="text-3xl font-bold text-red-400">{customers.filter(c => c.blocked).length}</p>
        </div>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by phone or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] placeholder-[var(--muted)] focus:outline-none focus:border-[var(--primary)]"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">ID</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Phone</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Name</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Orders</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden sm:table-cell">Joined</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCustomers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[var(--muted)]">
                    No customers found
                  </td>
                </tr>
              ) : (
                filteredCustomers.map((customer) => (
                  <tr key={customer.id} className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors">
                    <td className="p-4">
                      <span className="font-mono text-sm">{customer.id.slice(0, 8)}...</span>
                    </td>
                    <td className="p-4">
                      <span className="font-medium">{customer.phone}</span>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <span>{customer.name || 'N/A'}</span>
                    </td>
                    <td className="p-4 hidden lg:table-cell">
                      <span className="font-medium">{customer.total_orders}</span>
                    </td>
                    <td className="p-4 hidden sm:table-cell text-sm text-[var(--muted)]">
                      {formatDate(customer.created_at)}
                    </td>
                    <td className="p-4">
                      {customer.blocked ? (
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
                          Blocked
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => handleBlockCustomer(customer.id, !customer.blocked)}
                        disabled={blockingId === customer.id}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          customer.blocked
                            ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                            : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                        } disabled:opacity-50`}
                      >
                        {blockingId === customer.id ? '...' : customer.blocked ? 'Unblock' : 'Block'}
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
    </div>
  );
}
