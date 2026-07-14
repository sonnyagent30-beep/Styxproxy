'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { AdminTeamMember, AdminMeResponse, AdminRole } from '@/types';

export default function AdminTeamPage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [team, setTeam] = useState<AdminTeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  
  // Invite form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<AdminRole>('admin');
  const [inviting, setInviting] = useState(false);
  const [inviteMessage, setInviteMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    
    // Get current admin
    const meResult = await api.getAdminMe();
    if (meResult.error) {
      setError(meResult.error);
      setLoading(false);
      return;
    }
    
    const adminData = meResult.data;
    setAdmin(adminData || null);
    
    // Only SuperAdmin can view team
    if (adminData?.role !== 'superadmin') {
      setError('Access denied. Only SuperAdmins can view this page.');
      setLoading(false);
      return;
    }

    // Get team members
    const teamResult = await api.getAdminTeam();
    if (teamResult.error) {
      setError(teamResult.error);
    } else {
      setTeam(teamResult.data?.members || []);
    }
    
    setLoading(false);
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);
    setInviteMessage('');

    const result = await api.createAdminInvite({
      email: inviteEmail || undefined,
      role: inviteRole,
      expires_in_hours: 24,
      max_uses: 1,
    });

    if (result.error) {
      setInviteMessage(result.error);
    } else if (result.data) {
      setInviteMessage(`Invite created! Code: ${result.data.invite_code}`);
      setInviteEmail('');
      setInviteRole('admin');
      setShowInviteModal(false);
      // Reload team data
      loadData();
    }

    setInviting(false);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getRoleBadge = (role: AdminRole) => {
    const styles = {
      superadmin: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      admin: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      viewer: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };
    return styles[role] || styles.viewer;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  // Check if SuperAdmin
  if (admin?.role !== 'superadmin') {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-8 rounded-2xl bg-[var(--card)] border border-red-500/30 text-center">
          <h2 className="text-xl font-bold text-red-400 mb-2">Access Denied</h2>
          <p className="text-[var(--muted)]">Only SuperAdmins can manage the team.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">
            Team <span className="gradient-text">Management</span>
          </h1>
          <p className="text-[var(--muted)]">Manage admin accounts and permissions</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="px-6 py-2 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity"
        >
          + Invite Admin
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadData} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Team List */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 font-medium text-[var(--muted)]">Phone</th>
                <th className="text-left p-4 font-medium text-[var(--muted)]">Role</th>
                <th className="text-left p-4 font-medium text-[var(--muted)]">2FA</th>
                <th className="text-left p-4 font-medium text-[var(--muted)]">Created</th>
                <th className="text-left p-4 font-medium text-[var(--muted)]">Last Login</th>
                <th className="text-left p-4 font-medium text-[var(--muted)]">Status</th>
              </tr>
            </thead>
            <tbody>
              {team.map((member) => (
                <tr key={member.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="p-4 font-mono text-sm">{member.phone}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getRoleBadge(member.role)}`}>
                      {member.role}
                    </span>
                  </td>
                  <td className="p-4">
                    {member.totp_enabled ? (
                      <span className="text-green-400">✓ Enabled</span>
                    ) : (
                      <span className="text-[var(--muted)]">✕ Disabled</span>
                    )}
                  </td>
                  <td className="p-4 text-sm text-[var(--muted)]">
                    {formatDate(member.created_at)}
                  </td>
                  <td className="p-4 text-sm text-[var(--muted)]">
                    {member.last_used ? formatDate(member.last_used) : 'Never'}
                  </td>
                  <td className="p-4">
                    {member.locked_until ? (
                      <span className="text-red-400">🔒 Locked</span>
                    ) : member.failed_attempts > 0 ? (
                      <span className="text-yellow-400">⚠ {member.failed_attempts} fails</span>
                    ) : (
                      <span className="text-green-400">✓ Active</span>
                    )}
                  </td>
                </tr>
              ))}
              {team.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[var(--muted)]">
                    No other team members yet. Invite someone!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">Invite New Admin</h3>
            
            <form onSubmit={handleInvite} className="space-y-4">
              {inviteMessage && (
                <div className={`p-4 rounded-xl text-sm ${
                  inviteMessage.includes('created') 
                    ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                    : 'bg-red-500/10 border border-red-500/30 text-red-400'
                }`}>
                  {inviteMessage}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">
                  Email <span className="text-[var(--muted)]">(optional)</span>
                </label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="admin@company.com"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as AdminRole)}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                >
                  <option value="admin">Admin</option>
                  <option value="superadmin">SuperAdmin</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] font-medium hover:bg-[var(--card)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="flex-1 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {inviting ? 'Creating...' : 'Create Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
