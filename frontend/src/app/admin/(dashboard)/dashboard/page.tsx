'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { AdminStats, MetricsOverview } from '@/types';
import ErrorBoundary from '@/components/admin/ErrorBoundary';
import { DashboardSkeleton } from '@/components/admin/Skeleton';

type HealthState = {
  status: string;
  database: string;
  redis: string;
  litellm: { status: string; latency_ms?: number };
  ollama: { status: string; minicpm5_loaded?: boolean };
  m2_cloud: { status: string; latency_ms?: number };
  charon_available: boolean;
  charon_primary: string;
  charon_fallback: string;
};

const FALLBACK_HEALTH: HealthState = {
  status: 'unknown',
  database: 'unknown',
  redis: 'unknown',
  litellm: { status: 'unknown' },
  ollama: { status: 'unknown' },
  m2_cloud: { status: 'unknown' },
  charon_available: false,
  charon_primary: 'm2-cloud',
  charon_fallback: 'local-minicpm5',
};

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [health, setHealth] = useState<HealthState>(FALLBACK_HEALTH);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    setError('');
    const [statsRes, metricsRes, healthRes] = await Promise.all([
      api.getAdminStats(),
      api.getMetricsOverview(),
      api.getSystemHealth(),
    ]);
    if (statsRes.error) setError(statsRes.error);
    else setStats(statsRes.data || null);

    if (metricsRes.data) setMetrics(metricsRes.data);

    if (healthRes.data) {
      const h = healthRes.data;
      setHealth({
        status: h.status,
        database: h.services.database,
        redis: h.services.redis,
        litellm: h.services.litellm,
        ollama: h.services.ollama,
        m2_cloud: h.services.m2_cloud,
        charon_available: h.charon_available,
        charon_primary: h.charon_routing.primary,
        charon_fallback: h.charon_routing.fallback,
      });
    }
    setLoading(false);
  };

  const formatNGN = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatUSD = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  if (loading) {
    return (
      <ErrorBoundary>
        <DashboardSkeleton />
      </ErrorBoundary>
    );
  }

  // Health derived status
  const allGreen =
    health.status === 'healthy' &&
    health.database === 'connected' &&
    health.litellm.status === 'connected' &&
    health.charon_available;
  const healthLabel = allGreen ? 'All Systems Operational' : 'Degraded';
  const healthColor = allGreen ? 'text-green-400' : 'text-amber-400';
  const healthDot = allGreen ? 'bg-green-400' : 'bg-amber-400';

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
          <button onClick={loadAll} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Customers</p>
          <p className="text-3xl font-bold">
            {(stats?.total_customers ?? metrics?.total_customers ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active Orders</p>
          <p className="text-3xl font-bold">
            {(stats?.active_orders ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Revenue (NGN)</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {formatNGN(stats?.total_revenue_ngn ?? 0)}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Revenue (USD)</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {formatUSD(metrics?.total_revenue_usd ?? 0)}
          </p>
        </div>
      </div>

      {/* Secondary KPIs */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Orders</p>
          <p className="text-3xl font-bold">{(metrics?.total_orders ?? 0).toLocaleString()}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active Credentials</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {(stats?.active_credentials ?? metrics?.active_credentials ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Free Trials Today</p>
          <p className="text-3xl font-bold">{stats?.free_trials_today ?? 0}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">System Status</p>
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${healthDot}`} />
            <p className={`text-lg font-bold ${healthColor}`}>{healthLabel}</p>
          </div>
        </div>
      </div>

      {/* System Health Detail */}
      <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">System Health</h2>
          <button
            onClick={loadAll}
            className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            title="Refresh"
          >
            ↻ Refresh
          </button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <ServiceRow
            label="Database"
            value={health.database}
            ok={health.database === 'connected'}
          />
          <ServiceRow
            label="Redis"
            value={health.redis}
            ok={health.redis === 'connected' || health.redis === 'not_installed'}
          />
          <ServiceRow
            label="LiteLLM"
            value={
              health.litellm.status === 'connected'
                ? `${health.litellm.latency_ms?.toFixed(1) ?? '?'} ms`
                : health.litellm.status
            }
            ok={health.litellm.status === 'connected'}
          />
          <ServiceRow
            label="Ollama (MiniCPM5)"
            value={health.ollama.minicpm5_loaded ? 'loaded' : health.ollama.status}
            ok={health.ollama.status === 'connected' && !!health.ollama.minicpm5_loaded}
          />
          <ServiceRow
            label="M2 Cloud"
            value={
              health.m2_cloud.status === 'connected'
                ? `${health.m2_cloud.latency_ms?.toFixed(1) ?? '?'} ms`
                : health.m2_cloud.status
            }
            ok={health.m2_cloud.status === 'connected'}
          />
          <ServiceRow
            label="Charon Routing"
            value={`${health.charon_primary} → ${health.charon_fallback}`}
            ok={health.charon_available}
          />
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

function ServiceRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  const color = ok ? 'text-green-400' : 'text-amber-400';
  const dot = ok ? 'bg-green-400' : 'bg-amber-400';
  return (
    <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
      <p className="text-sm text-[var(--muted)]">{label}</p>
      <div className="flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${dot}`} />
        <p className={`text-sm font-medium ${color}`}>{value}</p>
      </div>
    </div>
  );
}
