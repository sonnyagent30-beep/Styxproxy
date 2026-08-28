
/* eslint-disable react-hooks/immutability */

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
  groq: { status: string; latency_ms?: number };
  charon_available: boolean;
  charon_primary: string;
  charon_fallback: string;
};

type CircuitBreaker = {
  failures: number;
  state: string;  // closed | open | half_open
  tripped_at: string | null;
};

type CircuitBreakerState = Record<string, CircuitBreaker>;

const FALLBACK_HEALTH: HealthState = {
  status: 'unknown',
  database: 'unknown',
  redis: 'unknown',
  groq: { status: 'unknown' },
  charon_available: false,
  charon_primary: 'groq',
  charon_fallback: 'none',
};

function HealthBadge({ label, value, ok }: { label: string; value: string; ok: string }) {
  const isOk = value === ok;
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-[var(--card)] border border-[var(--border)]">
      <div className={`w-2 h-2 rounded-full ${isOk ? 'bg-green-400' : 'bg-amber-400'}`} />
      <div>
        <p className="text-xs text-[var(--muted)]">{label}</p>
        <p className={`text-sm font-medium ${isOk ? 'text-green-400' : 'text-amber-400'}`}>{value}</p>
      </div>
    </div>
  );
}

function CircuitBadge({ state, failures }: { state: string; failures: number }) {
  if (state === 'closed') return <span className="text-xs px-2 py-1 rounded-full bg-green-400/10 text-green-400">Closed</span>;
  if (state === 'open') return <span className="text-xs px-2 py-1 rounded-full bg-red-400/10 text-red-400">Open ({failures})</span>;
  return <span className="text-xs px-2 py-1 rounded-full bg-amber-400/10 text-amber-400">Half-Open</span>;
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [health, setHealth] = useState<HealthState>(FALLBACK_HEALTH);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [charonStats, setCharonStats] = useState<{
    uptime_seconds: number;
    llm_configured: boolean;
    requests: { total: number; successful: number; escalated: number; llm_errors: number; rate_limited: number };
    tokens_used_total: number;
    by_channel: Record<string, number>;
    by_outcome: Record<string, number>;
    recent_errors: Array<string>;
    latency_ms: { samples: number; avg: number; max: number };
  } | null>(null);
  const [circuitBreakers, setCircuitBreakers] = useState<CircuitBreakerState>({});
  const [resetConfirm, setResetConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, metricsRes, healthRes, charonRes] = await Promise.all([
        api.getAdminStats().catch((e: Error) => ({ data: null, error: e?.message || 'stats failed' })),
        api.getMetricsOverview().catch((e: Error) => ({ data: null, error: e?.message || 'metrics failed' })),
        api.getSystemHealth().catch((e: Error) => ({ data: null, error: e?.message || 'health failed' })),
        api.getCharonStats().catch(() => ({ data: null, error: 'unavailable' })),
      ]);
      if (statsRes.error) setError(statsRes.error);
      else setStats(statsRes.data || null);

      if (metricsRes.data) setMetrics(metricsRes.data);

      if (healthRes.data) {
        const h = healthRes.data;
        // Defensive: /api/v1/health sometimes returns degraded payloads
        // without the full services object. Treat partial as unknown rather
        // than crashing the dashboard.
        const services = h.services ?? {};

      // Circuit breakers
      if (healthRes.data && 'circuit_breakers' in healthRes.data) {
        setCircuitBreakers((healthRes.data as any).circuit_breakers || {});
      }
        setHealth({
          status: h.status ?? 'unknown',
          database: services.database ?? 'unknown',
          redis: services.redis ?? 'unknown',
          groq: services.groq ?? { status: 'unknown' },
          charon_available: h.charon_available ?? false,
          charon_primary: h.charon_routing?.primary ?? 'unknown',
          charon_fallback: h.charon_routing?.fallback ?? 'unknown',
        });
      }

      if (charonRes.data) setCharonStats(charonRes.data);
    } catch (e) {
      // Last-resort guard: if Promise.all itself blows up (rare — usually
      // .catch() on each call above handles it), show the message instead
      // of letting the error bubble to the page-level error boundary.
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleResetCharon = async () => {
    setResetting(true);
    setResetMessage(null);
    const result = await api.resetCharon();
    if (result.error) {
      setResetMessage({ type: 'error', text: result.error });
    } else {
      setResetMessage({ type: 'success', text: result.data?.message || 'Charon reset' });
      setResetConfirm(false);
      // Refresh stats after reset
      const charonRes = await api.getCharonStats();
      if (charonRes.data) setCharonStats(charonRes.data);
    }
    setResetting(false);
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
    health.groq.status === 'connected' &&
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
          <p className="text-[var(--muted)] text-sm mb-1">Orders Today</p>
          <p className="text-3xl font-bold">
            {(stats?.active_orders ?? metrics?.orders_today ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Revenue This Month (NGN)</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {formatNGN(metrics?.revenue_this_month_ngn ?? 0)}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Revenue (USD)</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {formatUSD((metrics?.revenue_this_month_ngn ?? 0) / 1700)}
          </p>
        </div>
      </div>

      {/* Secondary KPIs */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Customers</p>
          <p className="text-3xl font-bold">{(stats?.total_customers ?? 0).toLocaleString()}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active Credentials</p>
          <p className="text-3xl font-bold text-[var(--primary)]">
            {(stats?.active_credentials ?? metrics?.active_proxies ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Free Trials Today</p>
          <p className="text-3xl font-bold">{stats?.free_trials_today ?? 0}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Escalations</p>
          <p className="text-3xl font-bold">{metrics?.escalations_open ?? 0}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">System Status</p>
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${healthDot}`} />
            <p className={`text-lg font-bold ${healthColor}`}>{healthLabel}</p>
          </div>
        </div>
      </div>

      {/* Plan Stock Overview */}
      {stats?.plan_counts && Object.keys(stats.plan_counts).length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Plan Stock Overview</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { key: 'ISP', label: 'ISP Proxies', color: 'text-blue-400', bg: 'bg-blue-500/20' },
              { key: 'DC', label: 'Datacenter', color: 'text-purple-400', bg: 'bg-purple-500/20' },
              { key: 'MOBILE', label: 'Mobile 4G', color: 'text-orange-400', bg: 'bg-orange-500/20' },
              { key: 'RESIDENTIAL', label: 'Residential', color: 'text-green-400', bg: 'bg-green-500/20' },
            ].map(({ key, label, color, bg }) => (
              <div key={key} className={`p-4 rounded-xl border border-[var(--border)] ${bg}`}>
                <p className={`text-sm font-medium ${color}`}>{label}</p>
                <p className={`text-3xl font-bold mt-1 ${color}`}>
                  {stats.plan_counts[key] ?? 0}
                </p>
                <p className="text-xs text-[var(--muted)] mt-1">active plans</p>
              </div>
            ))}
          </div>
        </div>
      )}

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
            label="Groq"
            value={
              health.groq.status === 'connected'
                ? `${health.groq.latency_ms?.toFixed(1) ?? '?'} ms`
                : health.groq.status
            }
            ok={health.groq.status === 'connected'}
          />
          <ServiceRow
            label="Charon Routing"
            value={`${health.charon_primary} → ${health.charon_fallback}`}
            ok={health.charon_available}
          />
        </div>
      </div>

      {/* Charon Ops Panel */}
      <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Charon Ops</h2>
          {!resetConfirm ? (
            <button
              onClick={() => {
                setResetConfirm(true);
                setResetMessage(null);
              }}
              className="px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-colors text-sm font-medium"
              title="Reset Charon runtime state (in-memory caches, conversation locks)"
            >
              Reset Charon
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-sm text-amber-400">Confirm reset?</span>
              <button
                onClick={handleResetCharon}
                disabled={resetting}
                className="px-4 py-2 rounded-xl bg-red-500 text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50 text-sm"
              >
                {resetting ? 'Resetting...' : 'Yes, reset'}
              </button>
              <button
                onClick={() => setResetConfirm(false)}
                disabled={resetting}
                className="px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {resetMessage && (
          <div
            className={`mb-4 p-3 rounded-xl text-sm ${
              resetMessage.type === 'success'
                ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}
          >
            {resetMessage.text}
          </div>
        )}

        {charonStats ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">Total Requests</p>
              <p className="text-2xl font-bold">{charonStats.requests.total.toLocaleString()}</p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">Successful</p>
              <p className="text-2xl font-bold text-green-400">{charonStats.requests.successful.toLocaleString()}</p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">LLM Errors</p>
              <p className="text-2xl font-bold text-red-400">{charonStats.requests.llm_errors.toLocaleString()}</p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">LLM Configured</p>
              <div className="flex items-center gap-2">
                <span className={`inline-block w-2 h-2 rounded-full ${charonStats.llm_configured ? 'bg-green-400' : 'bg-red-400'}`} />
                <p className={`text-sm font-medium ${charonStats.llm_configured ? 'text-green-400' : 'text-red-400'}`}>
                  {charonStats.llm_configured ? 'yes' : 'no'}
                </p>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">Escalated</p>
              <p className="text-2xl font-bold text-amber-400">{charonStats.requests.escalated.toLocaleString()}</p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">Tokens Used</p>
              <p className="text-2xl font-bold">{charonStats.tokens_used_total.toLocaleString()}</p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <p className="text-[var(--muted)] text-xs mb-1">Avg Latency</p>
              <p className="text-2xl font-bold">{charonStats.latency_ms.avg.toFixed(0)} ms</p>
            </div>
            {charonStats.recent_errors.length > 0 && (
              <div className="sm:col-span-2 lg:col-span-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                <span className="font-medium">Recent errors:</span> {charonStats.recent_errors[0]}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            Charon stats unavailable — endpoint may be guarded by superadmin role.
          </p>
        )}
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
