
// eslint-disable-next-line react-hooks/immutability, react-hooks/purity, react-hooks/set-state-in-effect
'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type {
  AdminMeResponse,
  AdminAllPermissionsResponse,
  AdminMyPermissionsResponse,
  PermissionChangeRequestResponse,
} from '@/types';

export default function AdminPermissionsPage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [allPerms, setAllPerms] = useState<AdminAllPermissionsResponse | null>(null);
  const [myPerms, setMyPerms] = useState<AdminMyPermissionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  // S14: permission change requests
  const [activeTab, setActiveTab] = useState<'permissions' | 'requests'>('permissions');
  const [requests, setRequests] = useState<PermissionChangeRequestResponse[]>([]);
  const [reqLoading, setReqLoading] = useState(false);
  const [reqError, setReqError] = useState('');
  const [reqStatusFilter, setReqStatusFilter] = useState<string>('pending');
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [reviewerNotes, setReviewerNotes] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');

    // Get current admin
    const meResult = await api.getAdminMe();
    if (meResult.error) {
      setError(meResult.error);
      setLoading(false);
      return;
    }
    setAdmin(meResult.data || null);

    // Get all permissions (catalog)
    const allResult = await api.getAllPermissions();
    if (allResult.error) {
      setError(allResult.error);
      setLoading(false);
      return;
    }
    setAllPerms(allResult.data || null);

    // Get my effective permissions
    const myResult = await api.getMyPermissions();
    if (myResult.data) {
      setMyPerms(myResult.data);
      // Expand all categories by default
      const cats = new Set(Object.keys(myResult.data.permissions_by_category));
      setExpandedCategories(cats);
    }

    setLoading(false);
  };

  const loadRequests = async (status?: string) => {
    setReqLoading(true);
    setReqError('');
    const result = await api.getPermissionRequests(
      status === 'all' ? undefined : (status as any),
    );
    if (result.error) {
      setReqError(result.error);
    } else {
      setRequests(result.data?.requests || []);
    }
    setReqLoading(false);
  };

  const handleAction = async (
    requestId: string,
    action: 'approve' | 'reject',
  ) => {
    setActioningId(requestId);
    const result = await api.actionPermissionRequest(requestId, action, reviewerNotes || undefined);
    setActioningId(null);
    if (result.error) {
      alert('Action failed: ' + result.error);
    } else {
      setRequests((prev) => prev.filter((r) => r.id !== requestId));
      setReviewerNotes('');
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRequests(reqStatusFilter);
  }, []);

  const isGranted = (code: string): boolean => {
    if (!myPerms) return false;
    for (const cat of Object.keys(myPerms.permissions_by_category)) {
      const found = myPerms.permissions_by_category[cat].find((p) => p.code === code);
      if (found) return found.granted;
    }
    return false;
  };

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const expandAll = () => {
    if (allPerms) setExpandedCategories(new Set(allPerms.categories));
  };

  const collapseAll = () => {
    setExpandedCategories(new Set());
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-[var(--muted)] animate-pulse">Loading permissions…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
        <p className="text-red-400 font-semibold">Error loading permissions</p>
        <p className="text-sm text-[var(--muted)] mt-1">{error}</p>
      </div>
    );
  }

  const isSuperAdmin = admin?.role === 'superadmin';
  const grantedCount = myPerms?.permission_count ?? 0;
  const totalCount = allPerms?.total ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Permissions</h1>
        <p className="text-[var(--muted)] mt-1">
          {isSuperAdmin
            ? '51 permission codes across 11 categories. Review what each admin effectively has.'
            : 'Your effective permissions. Contact a superadmin to request changes.'}
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        <button
          onClick={() => setActiveTab('permissions')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'permissions'
              ? 'border-[var(--primary)] text-[var(--foreground)]'
              : 'border-transparent text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          Permissions
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'requests'
              ? 'border-[var(--primary)] text-[var(--foreground)]'
              : 'border-transparent text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          Change Requests
          {requests.filter((r) => r.status === 'pending').length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-400">
              {requests.filter((r) => r.status === 'pending').length}
            </span>
          )}
        </button>
      </div>

      {/* Requests Tab */}
      {activeTab === 'requests' && (
        <RequestsTab
          requests={requests}
          loading={reqLoading}
          error={reqError}
          isSuperAdmin={isSuperAdmin}
          statusFilter={reqStatusFilter}
          onStatusFilterChange={(s) => { setReqStatusFilter(s); loadRequests(s); }}
          onAction={handleAction}
          actioningId={actioningId}
          reviewerNotes={reviewerNotes}
          onNotesChange={setReviewerNotes}
        />
      )}

      {/* Permissions Tab (existing content) */}
      {activeTab === 'permissions' && (
        <p className="text-[var(--muted)] mt-1">
          {isSuperAdmin
            ? '51 permission codes across 11 categories. Review what each admin effectively has.'
            : 'Your effective permissions. Contact a superadmin to request changes.'}
        </p>
      )}

      {/* Summary card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl bg-[var(--card)] border border-[var(--border)] p-4">
          <p className="text-sm text-[var(--muted)]">Your role</p>
          <p className="text-2xl font-bold mt-1">
            {admin?.role === 'superadmin' ? '🛡️ SuperAdmin' : admin?.role === 'admin' ? '👤 Admin' : '👁️ Viewer'}
          </p>
        </div>
        <div className="rounded-xl bg-[var(--card)] border border-[var(--border)] p-4">
          <p className="text-sm text-[var(--muted)]">Granted to you</p>
          <p className="text-2xl font-bold mt-1">
            {grantedCount} / {totalCount}
          </p>
        </div>
        <div className="rounded-xl bg-[var(--card)] border border-[var(--border)] p-4">
          <p className="text-sm text-[var(--muted)]">TOTP</p>
          <p className="text-2xl font-bold mt-1">
            {admin?.totp_enabled ? '✅ Enabled' : '⚠️ Not enabled'}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-sm hover:border-[var(--primary)] transition-colors"
          >
            Expand all
          </button>
          <button
            onClick={collapseAll}
            className="px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-sm hover:border-[var(--primary)] transition-colors"
          >
            Collapse all
          </button>
        </div>
        <button
          onClick={loadData}
          className="px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-sm hover:border-[var(--primary)] transition-colors"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Categories */}
      {allPerms &&
        allPerms.categories.map((cat) => {
          const perms = allPerms.permissions_by_category[cat] || [];
          const grantedInCat = perms.filter((p) => isGranted(p.code)).length;
          const expanded = expandedCategories.has(cat);
          return (
            <div
              key={cat}
              className="rounded-xl bg-[var(--card)] border border-[var(--border)] overflow-hidden"
            >
              <button
                onClick={() => toggleCategory(cat)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-[var(--card-hover)] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">{expanded ? '▼' : '▶'}</span>
                  <span className="font-semibold capitalize">{cat}</span>
                  <span className="text-sm text-[var(--muted)]">
                    {grantedInCat} / {perms.length} granted
                  </span>
                </div>
                <div className="w-32 h-2 bg-[var(--surface-2)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--primary)] transition-all"
                    style={{ width: `${(grantedInCat / perms.length) * 100}%` }}
                  />
                </div>
              </button>
              {expanded && (
                <div className="border-t border-[var(--border)]">
                  <table className="w-full text-sm">
                    <thead className="bg-[var(--surface-2)]">
                      <tr>
                        <th className="text-left px-4 py-2 font-medium">Status</th>
                        <th className="text-left px-4 py-2 font-medium">Code</th>
                        <th className="text-left px-4 py-2 font-medium">Description</th>
                        <th className="text-left px-4 py-2 font-medium">Sensitivity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {perms.map((p) => {
                        const granted = isGranted(p.code);
                        return (
                          <tr
                            key={p.code}
                            className="border-t border-[var(--border)] hover:bg-[var(--card-hover)]"
                          >
                            <td className="px-4 py-2">
                              {granted ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-500/15 text-green-400 text-xs font-medium">
                                  ✓ Granted
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--surface-2)] text-[var(--muted)] text-xs font-medium">
                                  ✗ Not granted
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-2 font-mono text-xs">{p.code}</td>
                            <td className="px-4 py-2 text-[var(--muted)]">{p.description}</td>
                            <td className="px-4 py-2">
                              {p.is_sensitive ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 text-xs font-medium">
                                  🔒 Sensitive
                                </span>
                              ) : (
                                <span className="text-xs text-[var(--muted)]">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}

      {/* Footer note for non-superadmins */}
      {!isSuperAdmin && (
        <div className="rounded-xl bg-blue-500/10 border border-blue-500/30 p-4">
          <p className="text-sm text-blue-400">
            ℹ️ Only superadmins can grant / revoke permissions. Contact{' '}
            <a href="mailto:oyebiyiayomide30@gmail.com" className="underline">
              oyebiyiayomide30@gmail.com
            </a>{' '}
            if you need additional permissions.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Requests Tab Component ──────────────────────────────────────────────────────

function RequestsTab({
  requests,
  loading,
  error,
  isSuperAdmin,
  statusFilter,
  onStatusFilterChange,
  onAction,
  actioningId,
  reviewerNotes,
  onNotesChange,
}: {
  requests: PermissionChangeRequestResponse[];
  loading: boolean;
  error: string;
  isSuperAdmin: boolean;
  statusFilter: string;
  onStatusFilterChange: (s: string) => void;
  onAction: (id: string, action: 'approve' | 'reject') => void;
  actioningId: string | null;
  reviewerNotes: string;
  onNotesChange: (n: string) => void;
}) {
  const filters = ['all', 'pending', 'approved', 'rejected', 'expired'];

  if (loading) {
    return <div className="text-[var(--muted)] animate-pulse py-8 text-center">Loading requests…</div>;
  }
  if (error) {
    return <div className="text-red-400 py-4">{error}</div>;
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => onStatusFilterChange(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              statusFilter === f
                ? 'bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/30'
                : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:border-[var(--primary)]/30'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {requests.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted)]">
          No {statusFilter === 'all' ? '' : statusFilter} requests found.
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((req) => (
            <div key={req.id} className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)]">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm font-medium">{req.permission_code}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      req.status === 'pending' ? 'bg-amber-500/10 text-amber-400' :
                      req.status === 'approved' ? 'bg-green-500/10 text-green-400' :
                      req.status === 'rejected' ? 'bg-red-500/10 text-red-400' :
                      'bg-gray-500/10 text-gray-400'
                    }`}>
                      {req.status}
                    </span>
                    <span className="text-xs text-[var(--muted)]">
                      {req.desired_state ? 'Grant' : 'Revoke'}
                    </span>
                  </div>
                  <p className="text-sm mt-1 text-[var(--muted)]">
                    Requested by <span className="text-[var(--foreground)]">{req.requested_by}</span>
                    {req.target_email && req.target_email !== req.requested_by && (
                      <> for <span className="text-[var(--foreground)]">{req.target_email}</span></>
                    )}
                  </p>
                  <p className="text-sm mt-1 italic text-[var(--muted)]">"{req.justification}"</p>
                  <p className="text-xs text-[var(--muted)] mt-2">
                    {new Date(req.created_at).toLocaleDateString()} · expires {new Date(req.expires_at).toLocaleDateString()}
                  </p>
                  {req.reviewer_notes && (
                    <p className="text-xs mt-1 text-[var(--muted)]">
                      Note: {req.reviewer_notes}
                    </p>
                  )}
                </div>

                {/* Action buttons — superadmin only, pending only */}
                {isSuperAdmin && req.status === 'pending' && (
                  <div className="flex flex-col gap-2 min-w-[120px]">
                    <textarea
                      value={reviewerNotes}
                      onChange={(e) => onNotesChange(e.target.value)}
                      placeholder="Notes (optional)"
                      className="w-full text-xs px-2 py-1.5 rounded-lg bg-[var(--background)] border border-[var(--border)] resize-none"
                      rows={2}
                    />
                    <button
                      onClick={() => onAction(req.id, 'approve')}
                      disabled={actioningId === req.id}
                      className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 disabled:opacity-50 transition-colors"
                    >
                      {actioningId === req.id ? 'Processing…' : 'Approve'}
                    </button>
                    <button
                      onClick={() => onAction(req.id, 'reject')}
                      disabled={actioningId === req.id}
                      className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 disabled:opacity-50 transition-colors"
                    >
                      {actioningId === req.id ? 'Processing…' : 'Reject'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
