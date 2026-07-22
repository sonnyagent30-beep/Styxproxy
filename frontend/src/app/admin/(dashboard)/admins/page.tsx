'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { Admin, AdminRole } from '@/types';

// Role badge colors
const roleStyles: Record<AdminRole, { bg: string; text: string; border: string }> = {
  superadmin: { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  admin: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
  viewer: { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' },
};

const ROLE_OPTIONS: { value: AdminRole; label: string }[] = [
  { value: 'superadmin', label: 'Superadmin' },
  { value: 'admin', label: 'Admin' },
  { value: 'viewer', label: 'Viewer' },
];

export default function AdminsPage() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  
  // Modals
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [showLockModal, setShowLockModal] = useState(false);
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  
  // Form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [invitePhone, setInvitePhone] = useState('');
  const [invitePassword, setInvitePassword] = useState('');
  const [inviteRole, setInviteRole] = useState<AdminRole>('admin');
  const [submitting, setSubmitting] = useState(false);
  
  // Selected admin for actions
  const [selectedAdmin, setSelectedAdmin] = useState<Admin | null>(null);
  const [newRole, setNewRole] = useState<AdminRole>('admin');
  
  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const limit = 20;

  const loadAdmins = useCallback(async () => {
    setLoading(true);
    setError('');
    
    const result = await api.getAdmins(page, limit);

    if (result.error) {
      setError(result.error);
    } else {
      setAdmins(result.data?.admins || []);
      setTotal(result.data?.pagination?.total_items || 0);
      setTotalPages(result.data?.pagination?.total_pages || 0);
    }
    
    setLoading(false);
  }, [page]);

  useEffect(() => {
    loadAdmins();
  }, [loadAdmins]);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim() || !invitePassword.trim() || !invitePhone.trim()) return;
    
    setSubmitting(true);
    const result = await api.createAdmin({
      email: inviteEmail.trim(),
      phone: invitePhone.trim(),
      password: invitePassword,
      role: inviteRole,
    });
    
    if (result.error) {
      showToast(result.error, 'error');
    } else {
      showToast('Admin invited successfully', 'success');
      setShowInviteModal(false);
      setInviteEmail('');
      setInvitePhone('');
      setInvitePassword('');
      setInviteRole('admin');
      loadAdmins();
    }
    setSubmitting(false);
  };

  const handleRoleChange = async () => {
    if (!selectedAdmin) return;
    
    setSubmitting(true);
    const result = await api.updateAdminRole(selectedAdmin.email, newRole);
    
    if (result.error) {
      showToast(result.error, 'error');
    } else {
      showToast('Role updated successfully', 'success');
      setShowRoleModal(false);
      setSelectedAdmin(null);
      loadAdmins();
    }
    setSubmitting(false);
  };

  const handleLock = async () => {
    if (!selectedAdmin) return;
    
    setSubmitting(true);
    const isLocked = selectedAdmin.locked;
    const result = isLocked 
      ? await api.unlockAdmin(selectedAdmin.email)
      : await api.lockAdmin(selectedAdmin.email);
    
    if (result.error) {
      showToast(result.error, 'error');
    } else {
      showToast(isLocked ? 'Admin unlocked successfully' : 'Admin locked successfully', 'success');
      setShowLockModal(false);
      setSelectedAdmin(null);
      loadAdmins();
    }
    setSubmitting(false);
  };

  const handleDeactivate = async () => {
    if (!selectedAdmin) return;
    
    setSubmitting(true);
    const result = await api.deactivateAdmin(selectedAdmin.email);
    
    if (result.error) {
      showToast(result.error, 'error');
    } else {
      showToast('Admin deactivated successfully', 'success');
      setShowDeactivateModal(false);
      setSelectedAdmin(null);
      loadAdmins();
    }
    setSubmitting(false);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Stats
  const totalAdmins = admins.length;
  const superadmins = admins.filter(a => a.role === 'superadmin').length;
  const locked = admins.filter(a => a.locked).length;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-6 py-3 rounded-xl shadow-lg ${
          toast.type === 'success' 
            ? 'bg-green-500/20 border border-green-500/30 text-green-400' 
            : 'bg-red-500/20 border border-red-500/30 text-red-400'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">
            Admin <span className="gradient-text">Team</span>
          </h1>
          <p className="text-[var(--muted)]">Manage admin accounts and permissions</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Invite Admin
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadAdmins} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Admins</p>
          <p className="text-3xl font-bold">{total}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Superadmins</p>
          <p className="text-3xl font-bold text-purple-400">{superadmins}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Locked</p>
          <p className="text-3xl font-bold text-red-400">{locked}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Email</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Role</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden sm:table-cell">TOTP</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden md:table-cell">Status</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm hidden lg:table-cell">Last Used</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border)]">
                    <td className="p-4"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-40"></div></td>
                    <td className="p-4"><div className="animate-pulse h-6 bg-[var(--card-hover)] rounded w-20"></div></td>
                    <td className="p-4 hidden sm:table-cell"><div className="animate-pulse h-6 bg-[var(--card-hover)] rounded w-12"></div></td>
                    <td className="p-4 hidden md:table-cell"><div className="animate-pulse h-6 bg-[var(--card-hover)] rounded w-16"></div></td>
                    <td className="p-4 hidden lg:table-cell"><div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-24"></div></td>
                    <td className="p-4"><div className="animate-pulse h-8 bg-[var(--card-hover)] rounded w-24"></div></td>
                  </tr>
                ))
              ) : admins.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-[var(--muted)]">
                    No admins found
                  </td>
                </tr>
              ) : (
                admins.map((admin) => {
                  const style = roleStyles[admin.role];
                  return (
                    <tr key={admin.id} className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors">
                      <td className="p-4 text-sm">{admin.email}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${style.bg} ${style.text} ${style.border}`}>
                          {admin.role}
                        </span>
                      </td>
                      <td className="p-4 hidden sm:table-cell">
                        {admin.totp_enabled ? (
                          <span className="text-green-400 text-sm">✓</span>
                        ) : (
                          <span className="text-[var(--muted)] text-sm">✗</span>
                        )}
                      </td>
                      <td className="p-4 hidden md:table-cell">
                        {admin.locked ? (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
                            Locked
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-sm text-[var(--muted)] hidden lg:table-cell">
                        {formatDate(admin.last_used)}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-1">
                          {/* Change Role */}
                          <button
                            onClick={() => {
                              setSelectedAdmin(admin);
                              setNewRole(admin.role);
                              setShowRoleModal(true);
                            }}
                            className="p-2 hover:bg-[var(--card-hover)] rounded-lg transition-colors"
                            title="Change role"
                          >
                            <svg className="w-4 h-4 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          
                          {/* Lock/Unlock */}
                          <button
                            onClick={() => {
                              setSelectedAdmin(admin);
                              setShowLockModal(true);
                            }}
                            className="p-2 hover:bg-[var(--card-hover)] rounded-lg transition-colors"
                            title={admin.locked ? 'Unlock' : 'Lock'}
                          >
                            {admin.locked ? (
                              <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
                              </svg>
                            ) : (
                              <svg className="w-4 h-4 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                              </svg>
                            )}
                          </button>
                          
                          {/* Deactivate */}
                          <button
                            onClick={() => {
                              setSelectedAdmin(admin);
                              setShowDeactivateModal(true);
                            }}
                            className="p-2 hover:bg-[var(--card-hover)] rounded-lg transition-colors"
                            title="Deactivate"
                          >
                            <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7a4 4 0 11-8 0 4 4 0 018 0zM9 14a6 6 0 00-6 6v1h12v-1a6 6 0 00-6-6zM21 12h-6" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
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

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowInviteModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Invite Admin</h2>
            </div>
            <form onSubmit={handleInvite}>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Email</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                    placeholder="admin@example.com"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Phone</label>
                  <input
                    type="tel"
                    value={invitePhone}
                    onChange={(e) => setInvitePhone(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                    placeholder="+234..."
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Initial Password</label>
                  <input
                    type="password"
                    value={invitePassword}
                    onChange={(e) => setInvitePassword(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                    placeholder="Enter password"
                    required
                    minLength={8}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as AdminRole)}
                    className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="p-6 border-t border-[var(--border)] flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !inviteEmail.trim() || !invitePassword}
                  className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {submitting ? 'Inviting...' : 'Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Role Change Modal */}
      {showRoleModal && selectedAdmin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowRoleModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Change Role</h2>
              <p className="text-sm text-[var(--muted)]">{selectedAdmin.email}</p>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-[var(--muted)]">Select a new role for this admin:</p>
              <div className="space-y-2">
                {ROLE_OPTIONS.map((opt) => (
                  <label key={opt.value} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] cursor-pointer transition-colors">
                    <input
                      type="radio"
                      name="role"
                      value={opt.value}
                      checked={newRole === opt.value}
                      onChange={(e) => setNewRole(e.target.value as AdminRole)}
                      className="w-4 h-4 accent-[var(--primary)]"
                    />
                    <span className="font-medium">{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowRoleModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRoleChange}
                disabled={submitting || newRole === selectedAdmin.role}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {submitting ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lock/Unlock Modal */}
      {showLockModal && selectedAdmin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowLockModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">
                {selectedAdmin.locked ? 'Unlock Admin' : 'Lock Admin'}
              </h2>
              <p className="text-sm text-[var(--muted)]">{selectedAdmin.email}</p>
            </div>
            <div className="p-6">
              <div className={`p-4 rounded-xl ${selectedAdmin.locked ? 'bg-green-500/10 border border-green-500/20' : 'bg-yellow-500/10 border border-yellow-500/20'}`}>
                <p className={selectedAdmin.locked ? 'text-green-400' : 'text-yellow-400'}>
                  {selectedAdmin.locked 
                    ? 'This admin will be able to log in again.' 
                    : 'This admin will be prevented from logging in until unlocked.'}
                </p>
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowLockModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleLock}
                disabled={submitting}
                className={`flex-1 px-4 py-2 rounded-xl font-medium transition-opacity disabled:opacity-50 ${
                  selectedAdmin.locked 
                    ? 'bg-green-500 text-white hover:bg-green-600' 
                    : 'bg-yellow-500 text-black hover:bg-yellow-600'
                }`}
              >
                {submitting ? 'Processing...' : selectedAdmin.locked ? 'Unlock' : 'Lock'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deactivate Modal */}
      {showDeactivateModal && selectedAdmin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowDeactivateModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold text-red-400">Deactivate Admin</h2>
              <p className="text-sm text-[var(--muted)]">{selectedAdmin.email}</p>
            </div>
            <div className="p-6">
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <p className="text-red-400 font-medium">Warning: This action cannot be undone</p>
                <p className="text-sm text-[var(--muted)] mt-2">
                  This admin will be set to viewer role and locked. They will no longer have admin access.
                </p>
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowDeactivateModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeactivate}
                disabled={submitting}
                className="flex-1 px-4 py-2 rounded-xl bg-red-500 text-white font-medium hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                {submitting ? 'Deactivating...' : 'Deactivate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
