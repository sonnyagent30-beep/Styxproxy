'use client';

import React, { useEffect, useState, useCallback } from 'react';
import api from '@/lib/api';

interface MaintenanceState {
  enabled: boolean;
  ready_at: string | null;
  message: string | null;
}

export default function MaintenanceAdminPage() {
  const [state, setState] = useState<MaintenanceState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [readyAt, setReadyAt] = useState<string>(''); // datetime-local format

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    const result = await api.getMaintenanceStatus();
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setState(result.data);
      setMessage(result.data.message || '');
      // Convert ISO → datetime-local string
      if (result.data.ready_at) {
        const d = new Date(result.data.ready_at);
        const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16);
        setReadyAt(local);
      } else {
        setReadyAt('');
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const handleToggle = async (enabled: boolean) => {
    setSaving(true);
    setError('');
    const payload: {
      enabled: boolean;
      ready_at: string | null;
      message: string;
    } = {
      enabled,
      ready_at: readyAt ? new Date(readyAt).toISOString() : null,
      message: message.trim(),
    };
    const result = await api.toggleMaintenance(payload);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setState(result.data);
    }
    setSaving(false);
  };

  const handleSaveMessage = async () => {
    if (!state) return;
    setSaving(true);
    setError('');
    const result = await api.toggleMaintenance({
      message: message.trim() || null,
      ready_at: readyAt ? new Date(readyAt).toISOString() : null,
    });
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setState(result.data);
    }
    setSaving(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-[var(--muted)]">
        Loading…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">
          Maintenance Mode
        </h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Freeze public-facing pages. Admin and webhook traffic continues normally.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Status banner */}
      <div
        className={`p-4 rounded-2xl border ${
          state?.enabled
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
        }`}
      >
        <div className="flex items-center gap-3">
          <span
            className={`relative flex h-3 w-3 ${
              state?.enabled ? 'text-amber-400' : 'text-emerald-400'
            }`}
          >
            <span className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-current" />
          </span>
          <span className="font-semibold">
            Maintenance mode is {state?.enabled ? 'ON' : 'OFF'}
          </span>
        </div>
        <p className="text-xs mt-2 opacity-80">
          {state?.enabled
            ? 'Public pages are now showing the maintenance screen. Admin can still log in and operate.'
            : 'Public site is fully available. Toggle on to freeze it.'}
        </p>
      </div>

      {/* Toggle buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => handleToggle(true)}
          disabled={saving || state?.enabled}
          className="flex-1 px-4 py-3 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 font-medium hover:bg-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Turn ON
        </button>
        <button
          onClick={() => handleToggle(false)}
          disabled={saving || !state?.enabled}
          className="flex-1 px-4 py-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-medium hover:bg-emerald-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Turn OFF
        </button>
      </div>

      {/* Message + ready_at config */}
      <div className="space-y-4 p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
        <div>
          <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
            Public message
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            placeholder="Optional message shown to visitors…"
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
            Estimated return time (optional)
          </label>
          <input
            type="datetime-local"
            value={readyAt}
            onChange={(e) => setReadyAt(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
          />
        </div>
        <button
          onClick={handleSaveMessage}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-[var(--primary)] text-black font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {saving ? 'Saving…' : 'Save message & ready time'}
        </button>
      </div>

      <div className="text-xs text-[var(--muted)] space-y-1">
        <p>• Admin/superadmin routes and webhook endpoints stay open during maintenance.</p>
        <p>• Public API routes return 503 with the message above.</p>
        <p>• All actions are logged in the audit log.</p>
      </div>
    </div>
  );
}
