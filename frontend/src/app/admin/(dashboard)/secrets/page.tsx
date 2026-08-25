'use client';

/* Secrets Vault — superadmin management of runtime env secrets.
 * Values are masked by the backend after write; the vault never round-trips
 * plaintext. Writes require TOTP step-up (handled by the api client headers). */

import { useCallback, useEffect, useState } from 'react';

type SecretRow = { key: string; masked: string; set: boolean };
type VaultData = { groups: Record<string, SecretRow[]>; other: SecretRow[]; env_path: string };

const apiBase = '/api/admin/secrets';

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
      const res = await fetch(apiBase, { credentials: 'include' });
      if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || `HTTP ${res.status}`);
      setData(await res.json());
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
      // TOTP step-up header is injected by the shared admin fetch wrapper when required.
      const res = await fetch(apiBase, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || `HTTP ${res.status}`);
      setMessage(`${key} saved. Restart the API to apply.`);
      setEditingKey(null);
      setEditValue('');
      await load();
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
      const res = await fetch(`${apiBase}/${key}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || `HTTP ${res.status}`);
      setMessage(`${key} removed. Restart the API to apply.`);
      await load();
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
      const res = await fetch(`${apiBase}/restart`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || `HTTP ${res.status}`);
      setMessage('API restarting… it will be back in a few seconds.');
      setTimeout(() => load(), 5000);
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

  if (loading) return <div className="animate-pulse text-[var(--muted)] p-6">Loading vault…</div>;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Secrets Vault</h1>
          <p className="text-xs text-[var(--muted)] mt-1 font-mono">{data?.env_path}</p>
        </div>
        <button onClick={restartApi} disabled={busy}
          className="px-4 py-2 rounded-xl bg-[var(--primary)] text-black text-sm font-semibold hover:opacity-90 disabled:opacity-50">
          ↻ Restart API
        </button>
      </div>

      <div className="mb-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-xs">
        Values are write-only — the vault shows masked previews and never returns plaintext after saving.
        Changes take effect after <strong>Restart API</strong>.
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}
      {message && <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">{message}</div>}

      {data && Object.entries(data.groups).map(([group, rows]) => (
        <section key={group} className="mb-6 rounded-xl bg-[var(--card)] border border-[var(--border)] overflow-hidden relative">
          <h2 className="px-4 py-3 text-sm font-bold uppercase tracking-wide bg-[var(--card-hover)]">{group}</h2>
          {rows.map(r => <Row key={r.key} row={r} />)}
        </section>
      ))}

      {data && data.other.length > 0 && (
        <section className="mb-6 rounded-xl bg-[var(--card)] border border-[var(--border)] overflow-hidden relative">
          <h2 className="px-4 py-3 text-sm font-bold uppercase tracking-wide bg-[var(--card-hover)]">Other</h2>
          {data.other.map(r => <Row key={r.key} row={r} />)}
        </section>
      )}

      {/* Add new secret */}
      <form onSubmit={e => { e.preventDefault(); save(newKey.trim().toUpperCase(), newValue); setNewKey(''); setNewValue(''); }}
        className="rounded-xl bg-[var(--card)] border border-dashed border-[var(--border)] p-4">
        <p className="text-sm font-semibold mb-3">Add a secret</p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input value={newKey} onChange={e => setNewKey(e.target.value.toUpperCase())}
            placeholder="KEY_NAME" className="w-full sm:w-56 px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none font-mono text-sm" />
          <input type="password" value={newValue} onChange={e => setNewValue(e.target.value)}
            placeholder="secret value…" className="flex-1 px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none font-mono text-sm" />
          <button type="submit" disabled={!newKey || !newValue || busy}
            className="px-4 py-2 rounded-lg bg-[var(--primary)] text-black text-sm font-semibold disabled:opacity-50">Add</button>
        </div>
      </form>
    </div>
  );
}
