'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type {
  AdminMeResponse,
  AdminAllPermissionsResponse,
  AdminMyPermissionsResponse,
} from '@/types';

export default function AdminPermissionsPage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [allPerms, setAllPerms] = useState<AdminAllPermissionsResponse | null>(null);
  const [myPerms, setMyPerms] = useState<AdminMyPermissionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

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

  useEffect(() => {
    // Fetch all permissions on mount
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
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
