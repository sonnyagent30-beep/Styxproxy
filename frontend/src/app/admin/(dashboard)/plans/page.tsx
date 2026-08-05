'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { COUNTRIES } from '@/lib/products';
import type { Plan, PlanCreate, PlanUpdate, PlanSetting, PlanSettingValue } from '@/types';

// ─── helpers ──────────────────────────────────────────────────────────────────

function getCountryFlag(code: string) {
  return COUNTRIES[code]?.flag ?? '🌍';
}
function getCountryName(code: string) {
  return COUNTRIES[code]?.name ?? code;
}
const fmt = (n: number) =>
  new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 }).format(n);

type Tab = 'plans' | 'settings';

// ─── Plan type badge ───────────────────────────────────────────────────────────

const PLAN_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  ISP:         { bg: 'bg-blue-500/20',   text: 'text-blue-400',   label: 'ISP' },
  DC:          { bg: 'bg-purple-500/20',text: 'text-purple-400', label: 'DC' },
  RESIDENTIAL: { bg: 'bg-green-500/20',  text: 'text-green-400',  label: 'Residential' },
  MOBILE:      { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'Mobile' },
};
function TypeBadge({ type }: { type: string }) {
  const s = PLAN_STYLES[type.toUpperCase()] ?? PLAN_STYLES.ISP;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${s.bg} ${s.text} border-transparent`}>
      {s.label}
    </span>
  );
}

// ─── Slide-over panel ─────────────────────────────────────────────────────────

interface PanelProps {
  plan: Plan | null;           // null = create mode
  onClose: () => void;
  onSaved: () => void;
}

function PlanPanel({ plan, onClose, onSaved }: PanelProps) {
  const isEdit = !!plan;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState<PlanCreate>({
    plan_code: plan?.plan_code ?? '',
    plan_type: plan?.plan_type ?? 'ISP',
    country: plan?.country ?? 'US',
    price_ngn: plan?.price_ngn ?? (plan?.plan_type === 'ISP' || plan?.plan_type === 'DC' ? 8000 : 0),
    price_per_gb: plan?.price_per_gb ?? (plan?.plan_type === 'MOBILE' || plan?.plan_type === 'RESIDENTIAL' ? 3000 : undefined),
    quantity: plan?.quantity ?? 1,
    duration_days: plan?.duration_days ?? 30,
    features: plan?.features ?? { features: [] },
    is_active: plan?.is_active ?? true,
    sort_order: plan?.sort_order ?? 0,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      let result;
      if (isEdit) {
        const updateData: PlanUpdate = {
          price_ngn: form.price_ngn,
          price_per_gb: form.price_per_gb,
          quantity: form.quantity,
          duration_days: form.duration_days,
          features: form.features,
          is_active: form.is_active,
          sort_order: form.sort_order,
        };
        result = await api.updatePlan(plan.id, updateData);
      } else {
        if ((form.plan_type === 'RESIDENTIAL' || form.plan_type === 'MOBILE') && !form.price_per_gb) {
          setError('Price per GB is required for Residential and Mobile plans.');
          setLoading(false);
          return;
        }
        result = await api.createPlan(form);
      }

      if (result.error) {
        setError(result.error);
      } else {
        onSaved();
      }
    } catch {
      setError('Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const countryOptions = Object.entries(COUNTRIES)
    .sort(([, a], [, b]) => a.name.localeCompare(b.name))
    .map(([code, info]) => (
      <option key={code} value={code}>{info.flag} {info.name} ({code})</option>
    ));

  const planTypes = [
    { value: 'ISP', label: 'ISP' },
    { value: 'DC', label: 'DC (Datacenter)' },
    { value: 'RESIDENTIAL', label: 'Residential' },
    { value: 'MOBILE', label: 'Mobile' },
  ];

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-50" onClick={onClose} />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-[var(--card)] border-l border-[var(--border)] z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <h2 className="text-lg font-bold">{isEdit ? 'Edit Plan' : 'Create Plan'}</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--card-hover)] transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form id="plan-form" onSubmit={handleSubmit} className="space-y-5">

            {/* Plan Code — create only */}
            {!isEdit && (
              <div>
                <label className="block text-sm font-medium mb-2">Plan Code</label>
                <input
                  type="text"
                  value={form.plan_code}
                  onChange={e => setForm(f => ({ ...f, plan_code: e.target.value.toUpperCase() }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] font-mono"
                  placeholder="ISP-NG-1"
                  required
                />
              </div>
            )}

            {/* Plan Type + Country */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Plan Type</label>
                <select
                  value={form.plan_type}
                  onChange={e => setForm(f => ({ ...f, plan_type: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  required={!isEdit}
                >
                  {planTypes.map(pt => (
                    <option key={pt.value} value={pt.value}>{pt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Country</label>
                <select
                  value={form.country}
                  onChange={e => setForm(f => ({ ...f, country: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  required={!isEdit}
                >
                  {countryOptions}
                </select>
              </div>
            </div>

            {/* Pricing */}
            <div>
              <label className="block text-sm font-medium mb-2">Price (NGN)</label>
              <input
                type="number"
                value={form.price_ngn}
                onChange={e => setForm(f => ({ ...f, price_ngn: parseFloat(e.target.value) || 0 }))}
                className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                min={0}
                step={100}
                required
              />
            </div>

            {/* Price per GB — res/mobile always shown */}
            {(form.plan_type === 'RESIDENTIAL' || form.plan_type === 'MOBILE') && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Price per GB (NGN)
                  <span className="text-red-400 ml-1">*</span>
                </label>
                <input
                  type="number"
                  value={form.price_per_gb ?? ''}
                  onChange={e => setForm(f => ({ ...f, price_per_gb: parseFloat(e.target.value) || undefined }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  min={0}
                  step={100}
                  placeholder="e.g. 3000"
                />
              </div>
            )}

            {/* Quantity + Duration */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Quantity</label>
                <input
                  type="number"
                  value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) || 1 }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  min={1}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Duration (days)</label>
                <input
                  type="number"
                  value={form.duration_days}
                  onChange={e => setForm(f => ({ ...f, duration_days: parseInt(e.target.value) || 30 }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  min={1}
                  required
                />
              </div>
            </div>

            {/* Features */}
            <div>
              <label className="block text-sm font-medium mb-2">Features (JSON)</label>
              <textarea
                value={JSON.stringify(form.features ?? {}, null, 2)}
                onChange={e => {
                  try {
                    setForm(f => ({ ...f, features: JSON.parse(e.target.value) }));
                  } catch { /* ignore incomplete JSON while typing */ }
                }}
                className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] font-mono text-sm"
                rows={4}
              />
            </div>

            {/* Sort Order + Active */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Sort Order</label>
                <input
                  type="number"
                  value={form.sort_order}
                  onChange={e => setForm(f => ({ ...f, sort_order: parseInt(e.target.value) || 0 }))}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                />
              </div>
              <div className="flex items-center gap-3 pt-7">
                <button
                  type="button"
                  onClick={() => setForm(f => ({ ...f, is_active: !f.is_active }))}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.is_active ? 'bg-green-500' : 'bg-gray-600'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.is_active ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
                <span className="text-sm font-medium">{form.is_active ? 'Active' : 'Inactive'}</span>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--border)] flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="plan-form"
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-[var(--primary)] text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? 'Saving...' : isEdit ? 'Update Plan' : 'Create Plan'}
          </button>
        </div>
      </div>
    </>
  );
}

// ─── Settings card ────────────────────────────────────────────────────────────

interface SettingsCardProps {
  setting: PlanSetting;
  onUpdate: (planType: string, value: any) => void;
}

function SettingsCard({ setting, onUpdate }: SettingsCardProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const v = setting.setting_value;
  const isPerGB = ['RESIDENTIAL', 'MOBILE'].includes(setting.plan_type.toUpperCase());
  const price = isPerGB ? v.price_per_gb : v.price_per_ip;
  const priceLabel = isPerGB ? 'Price/GB (NGN)' : 'Price/IP (NGN)';

  const [form, setForm] = useState({
    price: price ?? 0,
    setting_value: v as PlanSettingValue,
    countries: v.available_countries ?? [],
  });

  const toggleCountry = (code: string) => {
    setForm(f => ({
      ...f,
      countries: f.countries.includes(code)
        ? f.countries.filter(c => c !== code)
        : [...f.countries, code].sort(),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: any = {
        available_countries: form.countries,
      };
      if (isPerGB) payload.setting_value = { ...form.setting_value, price_per_gb: form.price };
      else payload.setting_value = { ...form.setting_value, price_per_ip: form.price };
      await onUpdate(setting.plan_type, payload);
      setEditing(false);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const typeInfo = PLAN_STYLES[setting.plan_type.toUpperCase()] ?? PLAN_STYLES.ISP;

  return (
    <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-semibold ${typeInfo.bg} ${typeInfo.text}`}>
            {typeInfo.label}
          </span>
          <div>
            <p className="font-semibold">{setting.plan_type}</p>
            <p className="text-sm text-[var(--muted)]">
              {form.countries.length} countries{isPerGB && v.gb_tiers?.length ? ` · ${v.gb_tiers.join(', ')} GB` : ''}
            </p>
          </div>
        </div>
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 rounded-xl border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors text-sm font-medium"
          >
            Edit
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 rounded-xl border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors text-sm"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-xl bg-[var(--primary)] text-white text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
      )}

      {/* View mode */}
      {!editing ? (
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">{priceLabel}</span>
            <span className="font-semibold text-[var(--primary)]">{fmt(price ?? 0)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">Rotation modes</span>
            <span className="font-medium">{v.rotation_modes?.length ? v.rotation_modes.join(', ') : '—'}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">GB tiers</span>
            <span className="font-medium">{v.gb_tiers?.length ? v.gb_tiers.join(', ') : '—'}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">Supports city</span>
            <span className={v.supports_city ? 'text-green-400' : 'text-gray-500'}>{v.supports_city ? 'Yes' : 'No'}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[var(--muted)]">Countries</span>
            <span className="font-medium">{form.countries.length}</span>
          </div>
        </div>
      ) : (
        /* Edit mode */
        <div className="space-y-4">
          {/* Price */}
          <div>
            <label className="block text-sm font-medium mb-2">{priceLabel}</label>
            <input
              type="number"
              value={form.price}
              onChange={e => setForm(f => ({ ...f, price: parseFloat(e.target.value) || 0 }))}
              className="w-full px-4 py-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
              min={0}
              step={100}
            />
          </div>

          {/* Countries checklist */}
          <div>
            <label className="block text-sm font-medium mb-2">Available Countries</label>
            <div className="max-h-64 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--background)]">
              {Object.entries(COUNTRIES)
                .sort(([, a], [, b]) => a.name.localeCompare(b.name))
                .map(([code, info]) => {
                  const checked = form.countries.includes(code);
                  return (
                    <label
                      key={code}
                      className="flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--card-hover)] cursor-pointer border-b border-[var(--border)] last:border-0"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleCountry(code)}
                        className="w-4 h-4 rounded accent-[#0AD25A]"
                      />
                      <span className="text-lg">{info.flag}</span>
                      <span className="text-sm flex-1">{info.name}</span>
                      <span className="text-xs text-[var(--muted)]">{code}</span>
                    </label>
                  );
                })}
            </div>
            <p className="text-xs text-[var(--muted)] mt-1">{form.countries.length} countries selected</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AdminPlansPage() {
  const [tab, setTab] = useState<Tab>('plans');

  // Plans state
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const totalPages = Math.ceil(total / 20);

  // Panel state
  const [panel, setPanel] = useState<{ plan: Plan | null } | null>(null);

  // Search + group state
  const [search, setSearch] = useState('');
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['ISP','DC','MOBILE','RESIDENTIAL']));

  // Settings state
  const [settings, setSettings] = useState<PlanSetting[]>([]);
  const [settingsLoading, setSettingsLoading] = useState(false);

  const limit = 500;  // load all plans for grouping

  const loadPlans = useCallback(async () => {
    setLoading(true);
    setError('');
    const result = await api.getPlans(page, limit);
    if (result.error) {
      setError(result.error);
    } else {
      setPlans(result.data?.data ?? []);
      setTotal(result.data?.pagination?.total_items ?? 0);
    }
    setLoading(false);
  }, [page]);

  const loadSettings = useCallback(async () => {
    setSettingsLoading(true);
    const result = await api.getPlanSettings();
    if (!result.error) {
      setSettings(result.data?.settings ?? []);
    }
    setSettingsLoading(false);
  }, []);

  useEffect(() => { loadPlans(); }, [loadPlans]);
  useEffect(() => { if (tab === 'settings') loadSettings(); }, [tab, loadSettings]);

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this plan?')) return;
    const result = await api.deletePlan(id);
    if (!result.error) loadPlans();
    else alert(result.error);
  };

  const handleUpdateSetting = async (planType: string, payload: any) => {
    const result = await api.updatePlanSettings(planType, payload);
    if (!result.error) loadSettings();
    else throw new Error(result.error);
  };

  // Stats
  const activeCount = plans.filter(p => p.is_active).length;
  const inactiveCount = plans.length - activeCount;

  return (
    <div className="max-w-7xl mx-auto">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold">Plans</h1>
          <p className="text-[var(--muted)] mt-1">Manage proxy plans, pricing, and plan type settings</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadPlans}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={() => setPanel({ plan: null })}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-semibold hover:opacity-90 transition-opacity text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Plan
          </button>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 mb-6 border-b border-[var(--border)]">
        {(['plans', 'settings'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              tab === t
                ? 'border-[var(--primary)] text-[var(--primary)]'
                : 'border-transparent text-[var(--muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {t === 'plans' ? 'Plans' : 'Plan Type Settings'}
          </button>
        ))}
      </div>

      {/* ── Plans tab ── */}
      {tab === 'plans' && (
        <>
          {/* Search + quick stats */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6">
            <div className="relative flex-1">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search by plan code or country..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] text-sm"
              />
            </div>
            <div className="flex gap-2 text-sm text-[var(--muted)] shrink-0">
              <span>{plans.length} plans</span>
              <span>&middot;</span>
              <span className="text-green-400">{activeCount} active</span>
              <span>&middot;</span>
              <span className="text-gray-400">{inactiveCount} inactive</span>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
              <span>{error}</span>
              <button onClick={loadPlans} className="underline hover:no-underline">Retry</button>
            </div>
          )}

          {/* Grouped plans by type */}
          {loading && plans.length === 0 ? (
            <div className="space-y-4">
              {[1,2,3,4].map(i => <div key={i} className="h-24 rounded-2xl animate-pulse bg-[var(--card)]" />)}
            </div>
          ) : (() => {
            const PLAN_TYPES = ['ISP', 'DC', 'MOBILE', 'RESIDENTIAL'];
            // Group plans
            const grouped: Record<string, Plan[]> = {};
            for (const pt of PLAN_TYPES) grouped[pt] = [];
            for (const p of plans) {
              const key = p.plan_type.toUpperCase();
              if (grouped[key]) grouped[key].push(p);
              else grouped['RESIDENTIAL'].push(p); // fallback
            }
            // Filter by search
            const q = search.toLowerCase();
            const filtered = (plans: Plan[]) => q
              ? plans.filter(p => p.plan_code.toLowerCase().includes(q) || p.country.toLowerCase().includes(q))
              : plans;
            const toggleType = (pt: string) => setExpandedTypes(prev => {
              const next = new Set(prev);
              next.has(pt) ? next.delete(pt) : next.add(pt);
              return next;
            });
            return (
              <div className="space-y-3">
                {PLAN_TYPES.map(pt => {
                  const typePlans = filtered(grouped[pt] || []);
                  const isExpanded = expandedTypes.has(pt);
                  const active = typePlans.filter(p => p.is_active).length;
                  const isPerGb = pt === 'MOBILE' || pt === 'RESIDENTIAL';
                  if (q && typePlans.length === 0) return null;
                  return (
                    <div key={pt} className="rounded-2xl border border-[var(--border)] overflow-hidden bg-[var(--card)]">
                      {/* Section header */}
                      <button
                        onClick={() => toggleType(pt)}
                        className="w-full flex items-center justify-between px-5 py-3 hover:bg-[var(--card-hover)] transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <TypeBadge type={pt} />
                          <span className="text-sm font-medium">{typePlans.length} products</span>
                          <span className="text-xs text-[var(--muted)]">&middot;</span>
                          <span className="text-xs text-green-400">{active} active</span>
                          {isPerGb && <span className="text-xs text-[var(--muted)]">&middot; per-GB pricing</span>}
                        </div>
                        <svg className={`w-4 h-4 text-[var(--muted)] transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      {/* Plans list */}
                      {isExpanded && (
                        <div className="border-t border-[var(--border)]">
                          {typePlans.length === 0 ? (
                            <div className="p-6 text-center text-[var(--muted)] text-sm">No products in this group</div>
                          ) : (
                            <table className="w-full">
                              <thead>
                                <tr className="border-b border-[var(--border)]">
                                  <th className="text-left p-3 pl-5 text-xs font-semibold text-[var(--muted)]">Plan Code</th>
                                  <th className="text-left p-3 text-xs font-semibold text-[var(--muted)]">Country</th>
                                  <th className="text-left p-3 text-xs font-semibold text-[var(--muted)]">Price</th>
                                  <th className="text-left p-3 text-xs font-semibold text-[var(--muted)]">GB Tier</th>
                                  <th className="text-left p-3 text-xs font-semibold text-[var(--muted)]">Status</th>
                                  <th className="text-right p-3 pr-5 text-xs font-semibold text-[var(--muted)]">Actions</th>
                                </tr>
                              </thead>
                              <tbody>
                                {typePlans.map(plan => (
                                  <tr key={plan.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--card-hover)] transition-colors">
                                    <td className="p-3 pl-5">
                                      <span className="font-mono text-sm">{plan.plan_code}</span>
                                    </td>
                                    <td className="p-3">
                                      <span className="mr-2">{getCountryFlag(plan.country)}</span>
                                      <span className="text-sm">{getCountryName(plan.country)}</span>
                                    </td>
                                    <td className="p-3">
                                      {isPerGb ? (
                                        <div>
                                          <span className="font-semibold text-[var(--primary)]">₦{Number(plan.price_per_gb || 0).toLocaleString()}/GB</span>
                                          <span className="text-xs text-[var(--muted)] ml-1">× {plan.quantity} GB</span>
                                        </div>
                                      ) : (
                                        <span className="font-semibold text-[var(--primary)]">{fmt(plan.price_ngn)}</span>
                                      )}
                                    </td>
                                    <td className="p-3 text-sm text-[var(--muted)]">{plan.quantity} GB</td>
                                    <td className="p-3">
                                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${plan.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                                        {plan.is_active ? 'Active' : 'Inactive'}
                                      </span>
                                    </td>
                                    <td className="p-3 pr-5 text-right">
                                      <button
                                        onClick={() => setPanel({ plan })}
                                        className="px-3 py-1 rounded-lg text-xs font-medium bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                                      >
                                        Edit
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </>
      )}

      {/* ── Settings tab ── */}
      {tab === 'settings' && (
        <>
          {settingsLoading ? (
            <div className="grid sm:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-48 rounded-2xl animate-pulse bg-[var(--card)]" />)}
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {settings.map(s => (
                <SettingsCard key={s.id} setting={s} onUpdate={handleUpdateSetting} />
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Slide-over panel ── */}
      {panel && (
        <PlanPanel
          plan={panel.plan}
          onClose={() => setPanel(null)}
          onSaved={() => { setPanel(null); loadPlans(); }}
        />
      )}
    </div>
  );
}
