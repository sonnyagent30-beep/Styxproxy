'use client';

/* Secrets Vault — superadmin management of runtime env secrets.
 * Values are masked by the backend after write; the vault never round-trips
 * plaintext. Writes require TOTP step-up (handled by the api client headers). */

import { useCallback, useEffect, useState } from 'react';
import api from '@/lib/api';

type SecretRow = { key: string; masked: string; set: boolean };
type VaultData = { groups: Record<string, SecretRow[]>; other: SecretRow[]; env_path: string };

export default function SecretsVaultPage() {
  const [data, setData] = useState<VaultData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [reveal, setReveal] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.getSecretsVault();
      if (result.error) {
        setError(result.error);
      } else if (result.data) {
        setData(result.data as VaultData);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load vault');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (key: string, value: string) => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await api.saveSecret(key, value);
      if (result.error) {
        setError(result.error);
      } else {
        setMessage(`${key} saved. Restart the API to apply.`);
        setEditingKey(null);
        setEditValue('');
        await load();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (key: string) => {
    if (!confirm(`Remove ${key} from .env? The API keeps its current value until restart.`)) return;
    setBusy(true);
    try {
      const result = await api.deleteSecret(key);
      if (result.error) {
        setError(result.error);
      } else {
        setMessage(`${key} removed. Restart the API to apply.`);
        await load();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    } finally {
      setBusy(false);
    }
  };

  const restartApi = async () => {
    if (!confirm('Restart styxproxy-api now? Checkout is briefly unavailable (~2s).')) return;
    setBusy(true);
    setMessage('');
    try {
      const result = await api.restartApi();
      if (result.error) {
        setError(result.error);
      } else {
        setMessage('API restarting… it will be back in a few seconds.');
        setTimeout(() => load(), 5000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Restart failed');
    } finally {
      setBusy(false);
    }
  };

  const toggleReveal = (k: string) =>
    setReveal(prev => { const n = new Set(prev); n.has(k) ? n.delete(k) : n.add(k); return n; });

  const Row = ({ row }: { row: SecretRow }) => (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border)] last:border-0">
      <div className="flex-1 min-w-0">
        <p className="font-mono text-sm font-semibold truncate">{row.key}</p>
        <p className="font-mono text-xs text-[var(--muted)] mt-0.5 select-all">
          {row.set ? row.masked : <span className="italic">not set</span>}
        </p>
      </div>
      <button onClick={() => { setEditingKey(row.key); setEditValue(''); }} disabled={busy}
        className="px-3 py-1.5 text-sm rounded-lg border border-[var(--border)] hover:border-[var(--primary)] transition-colors disabled:opacity-50">
        Edit
      </button>
      <button onClick={() => remove(row.key)} disabled={busy}
        className="px-3 py-1.5 text-sm rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50">
        Remove
      </button>
      {editingKey === row.key && (
        <form onSubmit={e => { e.preventDefault(); save(row.key, editValue); }}
          className="absolute right-4 z-10 flex flex-col gap-2 p-4 rounded-xl bg-[var(--card)] border border-[var(--primary)] shadow-xl w-96">
          <p className="text-sm font-semibold">{row.key}</p>
          <input autoFocus type="password" value={editValue} onChange={e => setEditValue(e.target.value)}
            placeholder="Paste new secret value…" className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none font-mono text-sm" />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setEditingKey(null)} className="px-3 py-1.5 text-sm rounded-lg border border-[var(--border)]">Cancel</button>
            <button type="submit" disabled={!editValue || busy} className="px-3 py-1.5 text-sm rounded-lg bg-[var(--primary)] text-black font-semibold disabled:opacity-50">Save</button>
          </div>
        </form>
      )}
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Secrets Vault</h1>
          <p className="text-[var(--muted)]">Manage runtime environment variables. Changes require API restart.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button onClick={() => { setNewKey(''); setNewValue(''); }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Secret
          </button>
          <button onClick={restartApi} disabled={busy}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-colors disabled:opacity-50">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Restart API
          </button>
        </div>
      </div>

      {message && (
        <div className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="text-green-300 hover:text-white">Dismiss</button>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-300 hover:text-white">Dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-32 mb-3"></div>
              <div className="animate-pulse h-6 bg-[var(--card-hover)] rounded w-64"></div>
            </div>
          ))}
        </div>
      ) : data ? (
        <div className="space-y-6">
          {Object.entries(data.groups).map(([group, rows]) => (
            <div key={group} className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--card-hover)]">
                <h2 className="font-semibold text-sm uppercase tracking-wider text-[var(--muted)]">{group}</h2>
              </div>
              <div className="divide-y divide-[var(--border)]">
                {rows.map(row => <Row key={row.key} row={row} />)}
              </div>
            </div>
          ))}
          {data.other && data.other.length > 0 && (
            <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--card-hover)]">
                <h2 className="font-semibold text-sm uppercase tracking-wider text-[var(--muted)]">Other</h2>
              </div>
              <div className="divide-y divide-[var(--border)]">
                {data.other.map(row => <Row key={row.key} row={row} />)}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center text-[var(--muted)] py-12">No secrets loaded.</div>
      )}

      {/* Add Secret Modal */}
      {newKey !== '' || newValue !== '' ? (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => { setNewKey(''); setNewValue(''); }}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Add Secret</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Key</label>
                <input type="text" value={newKey} onChange={e => setNewKey(e.target.value)} placeholder="e.g., MY_API_KEY"
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] font-mono" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Value</label>
                <input type="password" value={newValue} onChange={e => setNewValue(e.target.value)} placeholder="Secret value"
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] font-mono" />
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button onClick={() => { setNewKey(''); setNewValue(''); }}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors">Cancel</button>
              <button onClick={() => { save(newKey, newValue); setNewKey(''); setNewValue(''); }}
                disabled={!newKey.trim() || !newValue.trim() || busy}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50">Save</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
