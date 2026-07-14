'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { AdminStats } from '@/types';

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

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
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">
            Admin <span className="gradient-text">Dashboard</span>
          </h1>
          <p className="text-[var(--muted)]">Monitor your Styxproxy business</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
            {error}
          </div>
        )}

        {/* Stats Grid */}
        {stats && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-sm mb-1">Total Customers</p>
              <p className="text-3xl font-bold">{stats.total_customers.toLocaleString()}</p>
            </div>
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[--border]">
              <p className="text-[var(--muted)] text-sm mb-1">Active Orders</p>
              <p className="text-3xl font-bold">{stats.active_orders.toLocaleString()}</p>
            </div>
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-sm mb-1">Total Revenue</p>
              <p className="text-3xl font-bold text-[var(--primary)]">{formatCurrency(stats.total_revenue_ngn)}</p>
            </div>
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-sm mb-1">Free Trials Today</p>
              <p className="text-3xl font-bold">{stats.free_trials_today}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex space-x-2 mb-6 overflow-x-auto">
          {['overview', 'customers', 'orders', 'credentials', 'logs', 'charon'].map((tab) => (
            <button
              key={tab}
              onClick={() => {
                if (tab === 'charon') {
                  window.location.href = '/admin/charon';
                } else {
                  setActiveTab(tab);
                }
              }}
              className={`px-6 py-2 rounded-full font-medium capitalize transition-all whitespace-nowrap ${
                activeTab === tab
                  ? 'bg-[var(--primary)] text-black'
                  : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--card-hover)]">
                <div>
                  <p className="font-medium">Active Credentials</p>
                  <p className="text-sm text-[var(--muted)]">Currently active proxy credentials</p>
                </div>
                <p className="text-2xl font-bold text-[var(--primary)]">{stats?.active_credentials || 0}</p>
              </div>
              <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--card-hover)]">
                <div>
                  <p className="font-medium">System Status</p>
                  <p className="text-sm text-[var(--muted)]">Backend API health check</p>
                </div>
                <p className="text-2xl font-bold text-green-400">Healthy</p>
              </div>
            </div>
          )}

          {activeTab === 'customers' && (
            <div className="text-center py-12 text-[var(--muted)]">
              Customer management coming soon...
            </div>
          )}

          {activeTab === 'orders' && (
            <div className="text-center py-12 text-[var(--muted)]">
              Order management coming soon...
            </div>
          )}

          {activeTab === 'credentials' && (
            <div className="text-center py-12 text-[var(--muted)]">
              Credential management coming soon...
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="text-center py-12 text-[var(--muted)]">
              Audit logs coming soon...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
