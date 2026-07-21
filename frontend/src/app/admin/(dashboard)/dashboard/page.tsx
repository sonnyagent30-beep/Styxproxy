'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { AdminStats } from '@/types';
import ErrorBoundary from '@/components/admin/ErrorBoundary';
import { DashboardSkeleton } from '@/components/admin/Skeleton';

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    const result = await api.getAdminStats();
    if (result.error) {
      setError(result.error);
    } else {
      setStats(result.data || null);
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

  if (loading) {
    return (
      <ErrorBoundary>
        <DashboardSkeleton />
      </ErrorBoundary>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold mb-2">
          Dashboard <span className="gradient-text">Overview</span>
        </h1>
        <p className="text-[var(--muted)]">Monitor your Styxproxy business</p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadStats} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Customers</p>
          <p className="text-3xl font-bold">{stats?.total_customers.toLocaleString() ?? 0}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active Orders</p>
          <p className="text-3xl font-bold">{stats?.active_orders.toLocaleString() ?? 0}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Revenue</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {formatCurrency(stats?.total_revenue_ngn ?? 0)}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Free Trials Today</p>
          <p className="text-3xl font-bold">{stats?.free_trials_today ?? 0}</p>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Active Credentials</p>
              <p className="text-sm text-[var(--muted)]">Currently active proxy credentials</p>
            </div>
            <p className="text-3xl font-bold text-[var(--primary)]">
              {stats?.active_credentials ?? 0}
            </p>
          </div>
        </div>
        
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">System Status</p>
              <p className="text-sm text-[var(--muted)]">Backend API health check</p>
            </div>
            <p className="text-2xl font-bold text-green-400">● Healthy</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <a
            href="/admin/orders"
            className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
          >
            <p className="font-medium">View Orders</p>
            <p className="text-sm text-[var(--muted)]">Manage all orders</p>
          </a>
          <a
            href="/admin/customers"
            className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
          >
            <p className="font-medium">View Customers</p>
            <p className="text-sm text-[var(--muted)]">Customer list</p>
          </a>
          <a
            href="/admin/credentials"
            className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
          >
            <p className="font-medium">Credentials</p>
            <p className="text-sm text-[var(--muted)]">Proxy credentials</p>
          </a>
          <a
            href="/admin/charon"
            className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
          >
            <p className="font-medium">Charon</p>
            <p className="text-sm text-[var(--muted)]">Knowledge base</p>
          </a>
        </div>
      </div>
    </div>
  );
}
