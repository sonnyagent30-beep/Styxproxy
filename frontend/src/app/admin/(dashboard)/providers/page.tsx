'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { ProviderCost, ProviderCostsResponse } from '@/types';

export default function ProviderCostsPage() {
  const [data, setData] = useState<ProviderCostsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    
    const result = await api.getProviderCosts();
    
    if (result.error) {
      setError(result.error);
    } else {
      setData(result.data || null);
    }
    
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatCurrency = (amount: number, currency: 'USD' | 'NGN' = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const providers = data?.providers || [];
  
  // Calculate totals
  const totalProviders = providers.length;
  const totalOrders = providers.reduce((sum, p) => sum + p.total_orders, 0);
  const totalCost = providers.reduce((sum, p) => sum + p.total_cost_usd, 0);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Provider Costs</h1>
          <p className="text-[var(--muted)]">Cost breakdown per proxy provider</p>
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
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Provider Costs</h1>
          <p className="text-[var(--muted)]">Cost breakdown per proxy provider</p>
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

      {/* Note from backend */}
      {data?.note && (
        <div className="mb-6 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-400">
          {data.note}
        </div>
      )}

      {/* Stats Row */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Providers</p>
          <p className="text-3xl font-bold">{totalProviders}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Orders</p>
          <p className="text-3xl font-bold">{totalOrders}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Cost (USD)</p>
          <p className="text-3xl font-bold text-[var(--primary)]">{formatCurrency(totalCost)}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Avg Cost/Order</p>
          <p className="text-3xl font-bold">{totalOrders > 0 ? formatCurrency(totalCost / totalOrders) : formatCurrency(0)}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Provider</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Orders</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Total Cost (USD)</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Avg Cost</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Margin %</th>
              </tr>
            </thead>
            <tbody>
              {providers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[var(--muted)]">
                    No provider data available. Backend may not have provider tracking yet.
                  </td>
                </tr>
              ) : (
                providers.map((provider) => (
                  <tr
                    key={provider.provider_name}
                    className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <td className="p-4">
                      <span className="font-medium">{provider.provider_name}</span>
                    </td>
                    <td className="p-4">
                      <span>{provider.total_orders}</span>
                    </td>
                    <td className="p-4">
                      <span className="font-medium text-[var(--primary)]">
                        {formatCurrency(provider.total_cost_usd)}
                      </span>
                    </td>
                    <td className="p-4">
                      <span>
                        {provider.total_orders > 0
                          ? formatCurrency(provider.total_cost_usd / provider.total_orders)
                          : formatCurrency(0)}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={provider.margin_estimate_percent >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {provider.margin_estimate_percent >= 0 ? '+' : ''}{provider.margin_estimate_percent?.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
