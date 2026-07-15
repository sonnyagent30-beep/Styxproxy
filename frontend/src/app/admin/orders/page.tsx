'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { Order, OrderStatus, AdminStats, PaginatedResponse } from '@/types';

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;

  useEffect(() => {
    loadData();
  }, [page, statusFilter]);

  const loadData = async () => {
    setLoading(true);
    setError('');

    const [statsResult, ordersResult] = await Promise.all([
      api.getAdminStats(),
      api.getOrders(page, limit),
    ]);

    if (statsResult.error) {
      setError(statsResult.error);
    } else {
      setStats(statsResult.data || null);
    }

    if (ordersResult.error) {
      setError(ordersResult.error);
    } else {
      const allOrders = ordersResult.data?.data || [];
      setOrders(statusFilter === 'all' ? allOrders : allOrders.filter(o => o.status === statusFilter));
      setTotal(ordersResult.data?.pagination.total_items || 0);
    }

    setLoading(false);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: OrderStatus) => {
    const styles: Record<OrderStatus, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      paid: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      fulfilled: 'bg-green-500/20 text-green-400 border-green-500/30',
      active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      expired: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
      cancelled: 'bg-red-500/20 text-red-400 border-red-500/30',
      refunded: 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  const totalPages = Math.ceil(total / limit);

  const filteredOrders = statusFilter === 'all' ? orders : orders.filter(o => o.status === statusFilter);

  if (loading && orders.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Orders</h1>
          <p className="text-[var(--muted)]">Manage customer orders</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
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
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Orders</h1>
          <p className="text-[var(--muted)]">Manage customer orders</p>
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
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Orders</p>
          <p className="text-3xl font-bold">{total}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Pending</p>
          <p className="text-3xl font-bold text-yellow-400">{orders.filter(o => o.status === 'pending').length}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Fulfilled</p>
          <p className="text-3xl font-bold text-green-400">{orders.filter(o => o.status === 'fulfilled' || o.status === 'active').length}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Revenue</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {formatCurrency(stats?.total_revenue_ngn || 0)}
          </p>
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
          <option value="pending">Pending</option>
          <option value="paid">Paid</option>
          <option value="fulfilled">Fulfilled</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="cancelled">Cancelled</option>
          <option value="refunded">Refunded</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Order ID</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Product</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Amount</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden sm:table-cell">Date</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[var(--muted)]">
                    No orders found
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr
                    key={order.order_id}
                    className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] cursor-pointer transition-colors"
                    onClick={() => setSelectedOrder(order)}
                  >
                    <td className="p-4">
                      <span className="font-mono text-sm">{order.order_id.slice(0, 12)}...</span>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <div>
                        <p className="font-medium">{order.plan_type || 'N/A'}</p>
                        <p className="text-sm text-[var(--muted)]">{order.country || 'N/A'}</p>
                      </div>
                    </td>
                    <td className="p-4 hidden lg:table-cell">
                      <span className="font-medium text-[var(--primary)]">
                        {formatCurrency(order.amount_paid_ngn || 0)}
                      </span>
                    </td>
                    <td className="p-4">{getStatusBadge(order.status)}</td>
                    <td className="p-4 hidden sm:table-cell text-sm text-[var(--muted)]">
                      {formatDate(order.created_at)}
                    </td>
                    <td className="p-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedOrder(order);
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

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedOrder(null)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Order Details</h2>
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="p-2 hover:bg-[var(--card-hover)] rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Order ID</span>
                <span className="font-mono text-sm">{selectedOrder.order_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Status</span>
                {getStatusBadge(selectedOrder.status)}
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Product</span>
                <span>{selectedOrder.plan_type || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Country</span>
                <span>{selectedOrder.country || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Amount</span>
                <span className="font-medium text-[var(--primary)]">{formatCurrency(selectedOrder.amount_paid_ngn || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Created</span>
                <span>{formatDate(selectedOrder.created_at)}</span>
              </div>
              {selectedOrder.expires_at && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Expires</span>
                  <span>{formatDate(selectedOrder.expires_at)}</span>
                </div>
              )}
              {selectedOrder.styxproxy_credential && (
                <div className="mt-4 p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)]">
                  <p className="font-medium mb-2">Credential</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[var(--muted)]">Username</span>
                      <span>{selectedOrder.styxproxy_credential.bun_username}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--muted)]">IP</span>
                      <span>{selectedOrder.styxproxy_credential.upstream_proxy_ip || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--muted)]">Port</span>
                      <span>{selectedOrder.styxproxy_credential.upstream_proxy_port}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
