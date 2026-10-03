'use client';

// eslint-disable-next-line react-hooks/immutability, react-hooks/purity, react-hooks/set-state-in-effect

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type {
  AdminMeResponse,
  RlsPolicyResponse,
  RlsPolicyListResponse,
  RlsSafeStatus,
  RlsRolloutPlanResponse,
} from '@/types';
import AdminTotpStepUpModal from '@/components/AdminTotpStepUpModal';

export default function AdminRlsPage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [policyList, setPolicyList] = useState<RlsPolicyListResponse | null>(null);
  const [status, setStatus] = useState<RlsSafeStatus | null>(null);
  const [rolloutPlan, setRolloutPlan] = useState<RlsRolloutPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [needsStepUp, setNeedsStepUp] = useState(false);
  const [pendingAction, setPendingAction] = useState<{tableName: string; currentEnabled: boolean} | null>(null);
  const [filter, setFilter] = useState<'all' | 'enabled' | 'disabled'>('all');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');

    const meResult = await api.getAdminMe();
    if (meResult.error) {
      setError(meResult.error);
      setLoading(false);
      return;
    }
    setAdmin(meResult.data || null);

    const [listR, statusR, planR] = await Promise.all([
      api.getRlsPolicies(),
      api.getRlsStatus(),
      api.getRlsRolloutPlan(),
    ]);
    if (listR.error) setError(listR.error);
    if (listR.data) setPolicyList(listR.data);
    if (statusR.data) setStatus(statusR.data);
    if (planR.data) setRolloutPlan(planR.data);

    setLoading(false);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, []);

  const handleToggle = async (tableName: string, currentEnabled: boolean) => {
    setActionInProgress(tableName);
    const newState = !currentEnabled;
    const result = await api.toggleRlsPolicy(
      tableName,
      newState,
      newState ? `enabled via /admin/rls by ${admin?.email}` : 'disabled via /admin/rls',
    );
    setActionInProgress(null);
    if (result.error) {
      // If TOTP step-up required, prompt for code and retry
      if (result.error.includes('TOTP') || result.error.includes('step-up') || result.error.includes('403')) {
        setPendingAction({ tableName, currentEnabled });
        setNeedsStepUp(true);
        return;
      }
      setError(result.error);
    } else {
      await loadData();
    }
  };

  const handleTotpSuccess = async () => {
    setNeedsStepUp(false);
    if (pendingAction) {
      const { tableName, currentEnabled } = pendingAction;
      setPendingAction(null);
      // Retry the toggle now that TOTP step-up session is active
      setActionInProgress(tableName);
      const newState = !currentEnabled;
      const result = await api.toggleRlsPolicy(
        tableName,
        newState,
        newState ? `enabled via /admin/rls by ${admin?.email}` : 'disabled via /admin/rls',
      );
      setActionInProgress(null);
      if (result.error) {
        setError(result.error);
      } else {
        await loadData();
      }
    }
  };

  const handleRefresh = async () => {
    setActionInProgress('__refresh__');
    const result = await api.refreshRlsPolicies();
    setActionInProgress(null);
    if (result.error) {
      setError(result.error);
    } else {
      await loadData();
    }
  };

  const filteredPolicies = (): RlsPolicyResponse[] => {
    if (!policyList) return [];
    if (filter === 'enabled') return policyList.policies.filter((p) => p.policy_enabled);
    if (filter === 'disabled') return policyList.policies.filter((p) => !p.policy_enabled);
    return policyList.policies;
  };

  if (loading) {
    return (
      <div className="p-8">
        <p className="text-[var(--muted)]">Loading RLS state…</p>
      </div>
    );
  }

  // SuperAdmin-only gate
  if (admin?.role !== 'superadmin') {
    return (
      <div className="p-8" role="alert">
        <h1 className="text-2xl font-bold text-red-400">Access denied</h1>
        <p className="mt-2 text-[var(--foreground)]">
          The RLS admin page requires the <code>superadmin</code> role.
        </p>
      </div>
    );
  }

  const completionPct = rolloutPlan
    ? Math.round(
        (rolloutPlan.phases.filter((p) => p.completed).length /
          rolloutPlan.phases.length) *
          100,
      )
    : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-[var(--foreground)]">Row-Level Security (RLS)</h1>
        <p className="mt-2 text-[var(--muted)]">
          Sprint 15 — Postgres RLS policy toggle. Every toggle creates two policies:
          one for <code>styxproxy_app</code> (the eventual app role) and one admin
          bridge for <code>styxproxy</code> (current app user) so admin sessions
          keep working until the connection string is pinned.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-900/40 border border-red-700 p-4 text-red-200" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Status cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-[var(--card)] rounded-lg p-4 border border-[var(--border)]">
          <p className="text-xs uppercase text-[var(--muted)]">Total Tables</p>
          <p className="mt-1 text-3xl font-bold text-[var(--foreground)]">
            {status?.total_tables ?? policyList?.total ?? 0}
          </p>
        </div>
        <div className="bg-[var(--card)] rounded-lg p-4 border border-[var(--border)]">
          <p className="text-xs uppercase text-[var(--muted)]">RLS Enabled</p>
          <p className="mt-1 text-3xl font-bold text-green-400">
            {status?.rls_enabled_count ?? policyList?.enabled_count ?? 0}
          </p>
        </div>
        <div className="bg-[var(--card)] rounded-lg p-4 border border-[var(--border)]">
          <p className="text-xs uppercase text-[var(--muted)]">RLS Disabled</p>
          <p className="mt-1 text-3xl font-bold text-amber-400">
            {status?.rls_disabled_count ?? 0}
          </p>
        </div>
        <div className="bg-[var(--card)] rounded-lg p-4 border border-[var(--border)]">
          <p className="text-xs uppercase text-[var(--muted)]">Phase 2 Progress</p>
          <p className="mt-1 text-3xl font-bold text-[var(--primary)]">{completionPct}%</p>
          <div className="mt-2 h-1.5 bg-[var(--card-hover)] rounded overflow-hidden">
            <div
              className="h-full bg-[var(--primary)] transition-all"
              style={{ width: `${completionPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Bypass role status banner */}
      <div className="mb-6 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-[var(--foreground)]">
              <strong>Running role:</strong>{' '}
              <code className="bg-[var(--background)] px-2 py-0.5 rounded text-[var(--primary)]">
                {status?.current_user_role ?? 'unknown'}
              </code>
              {'  '}
              <strong className="ml-4">styxproxy_app role:</strong>{' '}
              <span className={status?.bypass_role_exists ? 'text-green-400' : 'text-red-400'}>
                {status?.bypass_role_exists ? '✓ exists' : '✗ missing'}
              </span>
              {'  '}
              <strong className="ml-4">Connection pinned:</strong>{' '}
              <span className={rolloutPlan?.connection_string_pinned ? 'text-green-400' : 'text-amber-400'}>
                {rolloutPlan?.connection_string_pinned ? '✓ yes' : '○ no (final Sprint 15 step)'}
              </span>
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={actionInProgress === '__refresh__'}
            className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:bg-[var(--card-hover)] text-[var(--foreground)] text-sm font-medium rounded-lg transition-colors"
          >
            {actionInProgress === '__refresh__' ? 'Refreshing…' : 'Refresh from pg_class'}
          </button>
        </div>
      </div>

      {/* Phase 2a-2h rollout plan */}
      {rolloutPlan && (
        <div className="mb-6">
          <h2 className="text-xl font-bold text-[var(--foreground)] mb-3">
            Rollout Plan (Phase 2a–2h)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {rolloutPlan.phases.map((phase) => (
              <div
                key={phase.phase}
                className={`rounded-lg border p-4 ${
                  phase.completed
                    ? 'bg-green-500/10 border-green-700'
                    : 'bg-[var(--card)] border-[var(--border)]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs uppercase text-[var(--muted)]">
                      Phase {phase.phase} · risk: {phase.risk}
                    </p>
                    <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                      {phase.completed ? '✓' : '○'} {phase.table_name}
                    </p>
                    <p className="mt-1 text-sm text-[var(--foreground)]">{phase.rationale}</p>
                  </div>
                  {phase.enabled_at && (
                    <p className="text-xs text-[var(--muted)] whitespace-nowrap">
                      {new Date(phase.enabled_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
          {rolloutPlan.next_phase === null && !rolloutPlan.connection_string_pinned && (
            <p className="mt-3 text-amber-300 text-sm">
              ✓ All phase 2 tables enabled. Final step: pin{' '}
              <code>DATABASE_URL=styxproxy_app</code> to make the policies actually
              enforce for the app session.
            </p>
          )}
        </div>
      )}

      {/* Filter + Table list */}
      <div className="mb-4 flex items-center gap-2">
        <span className="text-sm text-[var(--muted)]">Filter:</span>
        {(['all', 'enabled', 'disabled'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-xs rounded ${
              filter === f
                ? 'bg-[var(--primary)] text-[var(--foreground)]'
                : 'bg-[var(--card-hover)] text-[var(--foreground)] hover:bg-[var(--card-hover)]'
            }`}
          >
            {f}
          </button>
        ))}
        <span className="ml-auto text-sm text-[var(--muted)]">
          Showing {filteredPolicies().length} of {policyList?.total ?? 0}
        </span>
      </div>

      <div className="rounded-lg border border-[var(--border)] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--card)]">
            <tr>
              <th className="text-left p-3 text-[var(--foreground)]">Table</th>
              <th className="text-left p-3 text-[var(--foreground)]">Policy</th>
              <th className="text-left p-3 text-[var(--foreground)]">Status</th>
              <th className="text-left p-3 text-[var(--foreground)]">Applied</th>
              <th className="text-right p-3 text-[var(--foreground)]">Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredPolicies().map((p) => (
              <tr
                key={p.table_name}
                className="border-t border-[var(--border)] hover:bg-[var(--card)]/50"
              >
                <td className="p-3 font-mono text-[var(--foreground)]">{p.table_name}</td>
                <td className="p-3 font-mono text-xs text-[var(--foreground)]">{p.policy_name}</td>
                <td className="p-3">
                  {p.policy_enabled ? (
                    <span className="inline-block px-2 py-0.5 text-xs rounded bg-green-500/20 text-green-300">
                      enabled
                    </span>
                  ) : (
                    <span className="inline-block px-2 py-0.5 text-xs rounded bg-[var(--card-hover)] text-[var(--muted)]">
                      disabled
                    </span>
                  )}
                </td>
                <td className="p-3 text-xs text-[var(--muted)]">
                  {p.applied_at ? new Date(p.applied_at).toLocaleString() : '—'}
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => handleToggle(p.table_name, p.policy_enabled)}
                    disabled={actionInProgress === p.table_name}
                    className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
                      p.policy_enabled
                        ? 'bg-amber-600 hover:bg-amber-700 text-[var(--foreground)]'
                        : 'bg-green-600 hover:bg-green-700 text-[var(--foreground)]'
                    } disabled:bg-[var(--card-hover)]`}
                  >
                    {actionInProgress === p.table_name
                      ? '…'
                      : p.policy_enabled
                      ? 'Disable'
                      : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}