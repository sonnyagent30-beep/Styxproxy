'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { Order, OrderStatus, AdminStats, PaginatedResponse, OrderDetail, Plan } from '@/types';

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null);
  const [selectedRowOrder, setSelectedRowOrder] = useState<Order | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<OrderDetail | null>(null);
  const [searching, setSearching] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [refundOrder, setRefundOrder] = useState<OrderDetail | null>(null);
  const [refundReason, setRefundReason] = useState('');
  const [plans, setPlans] = useState<Plan[]>([]);
  const limit = 20;

  const loadData = useCallback(async () => {
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
  }, [page, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    // Load plans for create modal
    api.getPlans(1, 100).then(result => {
      if (result.data) {
        setPlans(result.data.data);
      }
    });
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 2,
    }).format(amount);
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

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    
    setSearching(true);
    setSearchResults(null);
    
    // Try to determine if it's an order_id, tx_ref, or phone
    const lookupData: {orderId?: string; txRef?: string; phone?: string} = {};
    
    if (searchQuery.startsWith('ADMIN-') || searchQuery.length > 10) {
      lookupData.orderId = searchQuery;
    } else if (searchQuery.includes('-')) {
      lookupData.txRef = searchQuery;
    } else {
      lookupData.phone = searchQuery;
    }
    
    const result = await api.lookupOrder(lookupData);
    
    if (result.error) {
      setError(result.error);
    } else {
      setSearchResults(result.data || null);
      setSelectedOrder(result.data || null);
    }
    
    setSearching(false);
  };

  const handleRefund = async () => {
    if (!refundOrder || !refundReason.trim()) return;
    
    const result = await api.refundOrder(refundOrder.order_id, refundReason);
    
    if (result.error) {
      setError(result.error);
    } else {
      setShowRefundModal(false);
      setRefundOrder(null);
      setRefundReason('');
      loadData();
      if (selectedOrder?.order_id === refundOrder.order_id) {
        setSelectedOrder({ ...refundOrder, status: 'refunded' });
      }
    }
  };

  const handleUpdateStatus = async (orderId: string, newStatus: string) => {
    const result = await api.updateOrderStatus(orderId, { status: newStatus });
    
    if (result.error) {
      setError(result.error);
    } else {
      loadData();
      if (selectedOrder?.order_id === orderId) {
        setSelectedOrder({ ...selectedOrder, status: newStatus as OrderStatus });
      }
    }
  };

  const totalPages = Math.ceil(total / limit);
  const filteredOrders = statusFilter === 'all' ? orders : orders.filter(o => o.status === statusFilter);

  const statsData = {
    total: total,
    pending: orders.filter(o => o.status === 'pending').length,
    active: orders.filter(o => o.status === 'active' || o.status === 'fulfilled').length,
    refunded: orders.filter(o => o.status === 'refunded').length,
  };

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
        <div className="flex gap-2">
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Order
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Order ID, Transaction Ref, or Phone..."
              className="w-full px-4 py-3 pl-12 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
            />
            <svg className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button
            type="submit"
            disabled={searching || !searchQuery.trim()}
            className="px-6 py-3 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {/* Search Result Banner */}
      {searchResults && (
        <div className="mb-6 p-4 rounded-xl bg-[var(--primary)]/10 border border-[var(--primary)]/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Found: {searchResults.order_id}</p>
              <p className="text-sm text-[var(--muted)]">
                {searchResults.customer_phone} • {searchResults.plan_type} • {formatCurrency(searchResults.amount_paid_ngn || 0)}
              </p>
            </div>
            {getStatusBadge(searchResults.status as OrderStatus)}
          </div>
        </div>
      )}

      {/* Stats Row */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Orders</p>
          <p className="text-3xl font-bold">{statsData.total}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Pending</p>
          <p className="text-3xl font-bold text-yellow-400">{statsData.pending}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active</p>
          <p className="text-3xl font-bold text-green-400">{statsData.active}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Refunded</p>
          <p className="text-3xl font-bold text-red-400">{statsData.refunded}</p>
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
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Customer</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Plan</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Amount</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden sm:table-cell">Created</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[var(--muted)]">
                    No orders found
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr
                    key={order.order_id}
                    className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] cursor-pointer transition-colors"
                    onClick={() => {
                      setSelectedRowOrder(order);
                      // Load full details
                      api.lookupOrder({ orderId: order.order_id }).then(result => {
                        if (result.data) {
                          setSelectedOrder(result.data);
                        }
                      });
                    }}
                  >
                    <td className="p-4">
                      <span className="font-mono text-sm">{order.order_id.slice(0, 16)}...</span>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <span className="text-sm">{order.customer_phone || 'N/A'}</span>
                    </td>
                    <td className="p-4 hidden lg:table-cell">
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
                          api.lookupOrder({ orderId: order.order_id }).then(result => {
                            if (result.data) {
                              setSelectedOrder(result.data);
                            }
                          });
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
        <OrderDetailModal
          order={selectedOrder}
          onClose={() => {
            setSelectedOrder(null);
            setSelectedRowOrder(null);
          }}
          onRefund={(order) => {
            setRefundOrder(order);
            setShowRefundModal(true);
          }}
          onUpdateStatus={handleUpdateStatus}
          formatCurrency={formatCurrency}
          formatDate={formatDate}
          getStatusBadge={getStatusBadge}
        />
      )}

      {/* Create Order Modal */}
      {showCreateModal && (
        <CreateOrderModal
          plans={plans}
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false);
            loadData();
          }}
          formatCurrency={formatCurrency}
        />
      )}

      {/* Refund Modal */}
      {showRefundModal && refundOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowRefundModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Process Refund</h2>
              <p className="text-sm text-[var(--muted)]">Order: {refundOrder.order_id}</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <p className="text-red-400 font-medium">Warning: This action cannot be undone</p>
                <p className="text-sm text-[var(--muted)]">The order will be marked as refunded and the credential will be revoked.</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Refund Reason</label>
                <textarea
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  rows={3}
                  placeholder="Enter reason for refund..."
                  required
                />
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowRefundModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRefund}
                disabled={!refundReason.trim()}
                className="flex-1 px-4 py-2 rounded-xl bg-red-500 text-white font-medium hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                Process Refund
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Order Detail Modal Component
function OrderDetailModal({
  order,
  onClose,
  onRefund,
  onUpdateStatus,
  formatCurrency,
  formatDate,
  getStatusBadge,
}: {
  order: OrderDetail;
  onClose: () => void;
  onRefund: (order: OrderDetail) => void;
  onUpdateStatus: (orderId: string, status: string) => void;
  formatCurrency: (amount: number) => string;
  formatDate: (dateStr: string) => string;
  getStatusBadge: (status: OrderStatus) => React.ReactNode;
}) {
  const [showPasswords, setShowPasswords] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const proxyString = order.bunche_credential 
    ? `${order.bunche_credential.protocol}://${order.bunche_credential.provider_username || order.bunche_credential.bun_username}:${order.bunche_credential.provider_password || 'password'}@${order.bunche_credential.upstream_proxy_ip}:${order.bunche_credential.upstream_proxy_port}`
    : null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[var(--border)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Order Details</h2>
            <button onClick={onClose} className="p-2 hover:bg-[var(--card-hover)] rounded-lg">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        <div className="p-6 space-y-6">
          {/* Order Info */}
          <div>
            <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Order Information</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Order ID</span>
                <span className="font-mono text-sm">{order.order_id}</span>
              </div>
              {order.tx_ref && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Transaction Ref</span>
                  <span className="font-mono text-sm">{order.tx_ref}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Customer</span>
                <span>{order.customer_phone || 'N/A'}</span>
              </div>
              {order.customer_name && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Name</span>
                  <span>{order.customer_name}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Status</span>
                {getStatusBadge(order.status as OrderStatus)}
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Plan</span>
                <span>{order.plan_type} - {order.plan_code}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Country</span>
                <span>{order.country || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Quantity</span>
                <span>{order.quantity}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Amount</span>
                <span className="font-medium text-[var(--primary)]">{formatCurrency(order.amount_paid_ngn || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Created</span>
                <span>{formatDate(order.created_at)}</span>
              </div>
              {order.fulfilled_at && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Fulfilled</span>
                  <span>{formatDate(order.fulfilled_at)}</span>
                </div>
              )}
              {order.expires_at && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Expires</span>
                  <span>{formatDate(order.expires_at)}</span>
                </div>
              )}
              {order.notes && (
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Notes</span>
                  <span className="text-right max-w-[200px]">{order.notes}</span>
                </div>
              )}
            </div>
          </div>

          {/* Refund Info */}
          {order.refund_requested && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
              <h3 className="text-sm font-medium text-red-400 mb-2">Refund Requested</h3>
              <p className="text-sm text-[var(--muted)]">{order.refund_reason || 'No reason provided'}</p>
            </div>
          )}

          {/* Credential Details */}
          {order.bunche_credential && (
            <div>
              <h3 className="text-sm font-medium text-[var(--muted)] mb-3">Proxy Credential</h3>
              <div className="p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] space-y-3">
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Username</span>
                  <span className="font-mono">{order.bunche_credential.bun_username}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Proxy IP</span>
                  <span className="font-mono">{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Protocol</span>
                  <span className="font-mono uppercase">{order.bunche_credential.protocol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Status</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    order.bunche_credential.status === 'active' 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {order.bunche_credential.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Data Used</span>
                  <span>{order.bunche_credential.gb_used.toFixed(2)} GB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted)]">Rotations</span>
                  <span>{order.bunche_credential.rotation_count}</span>
                </div>
                
                {/* Proxy Credentials Display */}
                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Proxy Credentials</span>
                    <button
                      onClick={() => setShowPasswords(!showPasswords)}
                      className="text-xs text-[var(--primary)] hover:underline"
                    >
                      {showPasswords ? 'Hide' : 'Reveal'}
                    </button>
                  </div>
                  {showPasswords ? (
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[var(--muted)]">Provider User</span>
                        <span className="font-mono">{order.bunche_credential.provider_username || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--muted)]">Provider Pass</span>
                        <span className="font-mono">{order.bunche_credential.provider_password || 'N/A'}</span>
                      </div>
                      {proxyString && (
                        <div className="mt-2">
                          <div className="flex justify-between mb-1">
                            <span className="text-[var(--muted)]">Full String</span>
                            <button
                              onClick={() => copyToClipboard(proxyString)}
                              className="text-xs text-[var(--primary)] hover:underline"
                            >
                              Copy
                            </button>
                          </div>
                          <code className="block p-2 rounded bg-[var(--background)] text-xs break-all">
                            {proxyString}
                          </code>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-[var(--muted)]">Click reveal to show credentials</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-4 border-t border-[var(--border)]">
            {order.status === 'pending' && (
              <button
                onClick={() => onUpdateStatus(order.order_id, 'fulfilled')}
                className="px-4 py-2 rounded-xl bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-colors"
              >
                Mark Fulfilled
              </button>
            )}
            {order.status === 'active' && (
              <>
                <button
                  onClick={() => onUpdateStatus(order.order_id, 'expired')}
                  className="px-4 py-2 rounded-xl bg-gray-500/20 text-gray-400 border border-gray-500/30 hover:bg-gray-500/30 transition-colors"
                >
                  Mark Expired
                </button>
                <button
                  onClick={() => onRefund(order)}
                  className="px-4 py-2 rounded-xl bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
                >
                  Issue Refund
                </button>
              </>
            )}
            {order.status === 'fulfilled' && (
              <button
                onClick={() => onUpdateStatus(order.order_id, 'active')}
                className="px-4 py-2 rounded-xl bg-[var(--primary)]/20 text-[var(--primary)] border border-[var(--primary)]/30 hover:bg-[var(--primary)]/30 transition-colors"
              >
                Activate
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Create Order Modal Component
function CreateOrderModal({
  plans,
  onClose,
  onCreated,
  formatCurrency,
}: {
  plans: Plan[];
  onClose: () => void;
  onCreated: () => void;
  formatCurrency: (amount: number) => string;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    customerPhone: '',
    planCode: '',
    country: 'NG',
    quantity: 1,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await api.createAdminOrder(form);

    if (result.error) {
      setError(result.error);
    } else {
      onCreated();
    }

    setLoading(false);
  };

  const selectedPlan = plans.find(p => p.plan_code === form.planCode);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[var(--border)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Create Order</h2>
            <button onClick={onClose} className="p-2 hover:bg-[var(--card-hover)] rounded-lg">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-2">Customer Phone</label>
            <input
              type="tel"
              value={form.customerPhone}
              onChange={(e) => setForm(f => ({ ...f, customerPhone: e.target.value }))}
              className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
              placeholder="+2348012345678"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Plan</label>
            <select
              value={form.planCode}
              onChange={(e) => setForm(f => ({ ...f, planCode: e.target.value }))}
              className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
              required
            >
              <option value="">Select a plan</option>
              {plans.filter(p => p.is_active).map(plan => (
                <option key={plan.id} value={plan.plan_code}>
                  {plan.plan_code} - {formatCurrency(plan.price_ngn)} ({plan.plan_type})
                </option>
              ))}
            </select>
            {selectedPlan && (
              <p className="mt-2 text-sm text-[var(--muted)]">
                {selectedPlan.duration_days} days • {selectedPlan.quantity} IP(s)
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Country</label>
            <select
              value={form.country}
              onChange={(e) => setForm(f => ({ ...f, country: e.target.value }))}
              className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
            >
              <option value="NG">Nigeria</option>
              <option value="US">United States</option>
              <option value="UK">United Kingdom</option>
              <option value="DE">Germany</option>
              <option value="JP">Japan</option>
              <option value="AU">Australia</option>
              <option value="SG">Singapore</option>
              <option value="KR">South Korea</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Quantity</label>
            <input
              type="number"
              value={form.quantity}
              onChange={(e) => setForm(f => ({ ...f, quantity: parseInt(e.target.value) || 1 }))}
              className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
              min="1"
              required
            />
          </div>

          {selectedPlan && (
            <div className="p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)]">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Total</span>
                <span className="text-xl font-bold text-[var(--primary)]">
                  {formatCurrency(selectedPlan.price_ngn * form.quantity)}
                </span>
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !form.customerPhone || !form.planCode}
              className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Order'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
