'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { COUNTRIES } from '@/lib/products';
import type { CountryCPT } from '@/types';

// ─── Types ────────────────────────────────────────────────────────────────────
type Tab = 'settings' | 'countries';

// Plan Settings types
interface BasePricing {
  price_per_ip: number | null;
  price_per_gb: number | null;
  pricing_model: string;
  gb_tiers?: number[];
}

interface CountryOverride {
  [country: string]: number;
}

interface PlanSettingItem {
  plan_type: string;
  base_pricing: BasePricing;
  country_overrides: CountryOverride;
}

// Product builder form
interface ProductForm {
  plan_type: string;
  pricing_model: string;
  price: string;
  countries: string[];
  is_active: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const PLAN_TYPES = [
  { value: 'DC', label: 'Datacenter' },
  { value: 'ISP', label: 'ISP Proxies' },
  { value: 'RESIDENTIAL', label: 'Residential' },
  { value: 'MOBILE', label: 'Mobile 4G' },
] as const;

const PLAN_TYPE_ORDER = ['DC', 'ISP', 'RESIDENTIAL', 'MOBILE'] as const;
const PLAN_TYPE_LABELS: Record<string, string> = {
  DC: 'Datacenter',
  ISP: 'ISP Proxies',
  RESIDENTIAL: 'Residential',
  MOBILE: 'Mobile 4G',
  dc: 'Datacenter',
  isp: 'ISP Proxies',
  residential: 'Residential',
  mobile: 'Mobile 4G',
};

const fmt = (n: number | null | undefined) =>
  n == null
    ? '—'
    : new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 }).format(n);

function getCountryFlag(code: string) {
  return COUNTRIES[code]?.flag ?? '🌍';
}
function getCountryName(code: string) {
  return COUNTRIES[code]?.name ?? code;
}

// All supported country codes (from the countries table — use the full list)
const ALL_COUNTRY_CODES = Object.keys(COUNTRIES).sort((a, b) =>
  getCountryName(a).localeCompare(getCountryName(b))
);

// ─── Country Row (Countries tab) ──────────────────────────────────────────────
interface CountryRowProps {
  country: CountryCPT;
  onToggle: (planType: string, enabled: boolean) => void;
  onEditPrice: (planType: string, currentPrice: number | null) => void;
  savingTypes: Set<string>;
}

function CountryRow({ country, onToggle, onEditPrice, savingTypes }: CountryRowProps) {
  const enabledTypes = new Set(country.enabled_plan_types || []);

  return (
    <tr className="border-b border-[var(--border)] hover:bg-[var(--background)]/50 transition-colors">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getCountryFlag(country.code)}</span>
          <div>
            <div className="font-medium text-[var(--foreground)]">{country.name}</div>
            <div className="text-xs text-[var(--muted)]">{country.code}</div>
          </div>
        </div>
      </td>
      {PLAN_TYPE_ORDER.map((type) => {
        const isEnabled = enabledTypes.has(type);
        const saving = savingTypes.has(`${country.code}:${type}`);
        const ptStatus = (country as any).plan_types?.[type];
        const currentPrice = ptStatus
          ? (type === 'DC' || type === 'ISP' ? ptStatus.price_per_ip : ptStatus.price_per_gb)
          : null;

        return (
          <td key={type} className="px-4 py-3 text-center">
            <div className="flex flex-col items-center gap-1">
              <button
                onClick={() => !saving && onToggle(type, !isEnabled)}
                disabled={saving}
                className={`relative w-10 h-5 rounded-full transition-colors disabled:opacity-40 ${
                  isEnabled ? 'bg-green-500' : 'bg-gray-600'
                }`}
              >
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                  isEnabled ? 'translate-x-5' : 'translate-x-0'
                }`} />
              </button>
              <button
                onClick={() => isEnabled && onEditPrice(type, currentPrice)}
                className={`text-xs px-1.5 py-0.5 rounded transition-colors ${
                  isEnabled
                    ? 'bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20'
                    : 'text-[var(--muted)]'
                }`}
              >
                {isEnabled ? '₦ Set' : '—'}
              </button>
            </div>
          </td>
        );
      })}
    </tr>
  );
}

// ─── Edit Modal (Countries tab) ────────────────────────────────────────────────
interface EditModalProps {
  country: CountryCPT;
  planType: string;
  enabled: boolean;
  currentPrice: number | null;
  onSave: (data: { enabled: boolean; price_per_gb: number | null; price_per_ip: number | null }) => void;
  onClose: () => void;
  saving: boolean;
}

function EditModal({ country, planType, enabled, currentPrice, onSave, onClose, saving }: EditModalProps) {
  const isIP = planType === 'DC' || planType === 'ISP';
  const [price, setPrice] = useState(currentPrice != null ? String(currentPrice) : '');
  const [isEnabled, setIsEnabled] = useState(enabled);

  const parsed = parseFloat(price);

  const handleSave = () => {
    onSave({
      enabled: isEnabled,
      price_per_gb: isIP ? null : (parsed || 0),
      price_per_ip: isIP ? (parsed || 0) : null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-sm p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl">
        <h2 className="text-lg font-bold text-[var(--foreground)] mb-1">
          {getCountryFlag(country.code)} {country.name}
        </h2>
        <p className="text-sm text-[var(--muted)] mb-5">
          {PLAN_TYPE_LABELS[planType] ?? planType} Pricing
        </p>

        <label className="flex items-center gap-3 mb-4 cursor-pointer select-none">
          <div
            onClick={() => setIsEnabled(!isEnabled)}
            className={`relative w-11 h-6 rounded-full transition-colors ${isEnabled ? 'bg-green-500' : 'bg-gray-600'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
              isEnabled ? 'translate-x-5' : 'translate-x-0'
            }`} />
          </div>
          <span className="text-sm text-[var(--foreground)]">{isEnabled ? 'Enabled' : 'Disabled'}</span>
        </label>

        <div className="mb-5">
          <label className="block text-sm font-medium text-[var(--muted)] mb-2">
            Price per {isIP ? 'IP/month (₦)' : 'GB (₦)'}
          </label>
          <input
            type="number" min={0} step={100}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder={currentPrice != null ? String(currentPrice) : '0'}
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
          />
          <p className="text-xs text-[var(--muted)] mt-1">Current: <strong>{fmt(currentPrice)}</strong></p>
        </div>

        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--background)]">Cancel</button>
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Product Builder Form ──────────────────────────────────────────────────────
interface ProductBuilderProps {
  onCreated: () => void;
}

function ProductBuilder({ onCreated }: ProductBuilderProps) {
  const [form, setForm] = useState<ProductForm>({
    plan_type: 'DC',
    pricing_model: 'per_IP',
    price: '',
    countries: [],
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showCountryPicker, setShowCountryPicker] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');

  const isIP = form.pricing_model === 'per_IP';

  const filteredCountries = ALL_COUNTRY_CODES.filter((code) =>
    getCountryName(code).toLowerCase().includes(countrySearch.toLowerCase()) ||
    code.toLowerCase().includes(countrySearch.toLowerCase())
  );

  const toggleCountry = (code: string) => {
    setForm((prev) => ({
      ...prev,
      countries: prev.countries.includes(code)
        ? prev.countries.filter((c) => c !== code)
        : [...prev.countries, code],
    }));
  };

  const handleSubmit = async () => {
    if (!form.price || parseFloat(form.price) <= 0) {
      setError('Enter a valid price'); return;
    }
    if (form.countries.length === 0) {
      setError('Select at least one country'); return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);

    const res = await api.createProductsBulk({
      plan_type: form.plan_type,
      pricing_model: form.pricing_model,
      price: parseFloat(form.price),
      countries: form.countries,
      is_active: form.is_active,
    });

    if (res.error) {
      setError('Failed: ' + res.error);
    } else {
      const data = res.data as any;
      const total = data.plans_created + data.cpt_rows_created + data.cpt_rows_updated;
      setSuccess(
        `Created ${data.plans_created} plan(s) — ${data.cpt_rows_created} new country entries, ${data.cpt_rows_updated} updated`
      );
      setForm((prev) => ({ ...prev, countries: [], price: '' }));
      onCreated();
    }
    setSaving(false);
  };

  return (
    <div className="space-y-5">
      {/* Success banner */}
      {success && (
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500 text-green-500 text-sm flex items-center justify-between">
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="text-green-400 hover:text-green-300 ml-4">✕</button>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">✕</button>
        </div>
      )}

      {/* Form */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 space-y-4">

        {/* Row 1: Plan type + Pricing model */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[var(--muted)] mb-2">Proxy Type</label>
            <div className="flex gap-2">
              {PLAN_TYPES.map((pt) => (
                <button
                  key={pt.value}
                  onClick={() => setForm((f) => ({
                    ...f,
                    plan_type: pt.value,
                    pricing_model: pt.value === 'RESIDENTIAL' || pt.value === 'MOBILE' ? 'per_GB' : 'per_IP',
                  }))}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm border transition-colors ${
                    form.plan_type === pt.value
                      ? 'bg-[var(--primary)] text-white border-[var(--primary)]'
                      : 'bg-[var(--background)] text-[var(--muted)] border-[var(--border)] hover:border-[var(--primary)]'
                  }`}
                >
                  {pt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--muted)] mb-2">Pricing Model</label>
            <div className="flex gap-2 h-[42px]">
              {['per_IP', 'per_GB'].map((pm) => {
                const disabled = (form.plan_type === 'RESIDENTIAL' || form.plan_type === 'MOBILE') && pm === 'per_IP'
                  || (form.plan_type === 'DC' || form.plan_type === 'ISP') && pm === 'per_GB';
                return (
                  <button
                    key={pm}
                    disabled={disabled}
                    onClick={() => !disabled && setForm((f) => ({ ...f, pricing_model: pm }))}
                    className={`flex-1 px-3 py-2 rounded-lg text-sm border transition-colors ${
                      form.pricing_model === pm
                        ? 'bg-[var(--primary)] text-white border-[var(--primary)]'
                        : disabled
                        ? 'bg-[var(--background)] text-[var(--muted)] border-[var(--border)] opacity-40 cursor-not-allowed'
                        : 'bg-[var(--background)] text-[var(--muted)] border-[var(--border)] hover:border-[var(--primary)]'
                    }`}
                  >
                    {pm === 'per_IP' ? 'per IP' : 'per GB'}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Row 2: Price + Active toggle */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[var(--muted)] mb-2">
              Price (₦ {isIP ? 'per IP/month' : 'per GB'})
            </label>
            <input
              type="number"
              min={1}
              step={100}
              value={form.price}
              onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
              placeholder="e.g. 8000"
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
            />
          </div>

          <div className="flex flex-col">
            <label className="block text-sm font-medium text-[var(--muted)] mb-2">Status</label>
            <div className="flex items-center h-[42px] gap-3">
              <div
                onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
                className={`relative w-11 h-6 rounded-full transition-colors cursor-pointer ${form.is_active ? 'bg-green-500' : 'bg-gray-600'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.is_active ? 'translate-x-5' : 'translate-x-0'}`} />
              </div>
              <span className="text-sm text-[var(--foreground)]">{form.is_active ? 'Active' : 'Inactive'}</span>
            </div>
          </div>
        </div>

        {/* Row 3: Countries */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-[var(--muted)]">
              Countries ({form.countries.length} selected)
            </label>
            <button
              type="button"
              onClick={() => setShowCountryPicker((v) => !v)}
              className="text-sm text-[var(--primary)] hover:underline"
            >
              {showCountryPicker ? 'Done selecting' : 'Select countries'}
            </button>
          </div>

          {/* Selected countries chips */}
          {form.countries.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {form.countries.map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-[var(--primary)]/20 text-[var(--primary)] border border-[var(--primary)]/30"
                >
                  {getCountryFlag(code)} {code}
                  <button
                    onClick={() => toggleCountry(code)}
                    className="ml-0.5 hover:text-white"
                  >✕</button>
                </span>
              ))}
            </div>
          )}

          {/* Country picker dropdown */}
          {showCountryPicker && (
            <div className="border border-[var(--border)] rounded-lg bg-[var(--background)] overflow-hidden">
              <div className="p-2 border-b border-[var(--border)]">
                <input
                  type="text"
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  placeholder="Search countries..."
                  className="w-full px-3 py-1.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  autoFocus
                />
              </div>
              <div className="max-h-52 overflow-y-auto divide-y divide-[var(--border)]">
                {filteredCountries.length === 0 && (
                  <p className="p-3 text-sm text-[var(--muted)] text-center">No countries found</p>
                )}
                {filteredCountries.map((code) => {
                  const selected = form.countries.includes(code);
                  return (
                    <label
                      key={code}
                      className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-[var(--card)] transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleCountry(code)}
                        className="w-4 h-4 rounded accent-[var(--primary)]"
                      />
                      <span className="text-lg">{getCountryFlag(code)}</span>
                      <div className="flex-1">
                        <div className="text-sm text-[var(--foreground)]">{getCountryName(code)}</div>
                        <div className="text-xs text-[var(--muted)]">{code}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Summary + Submit */}
        {form.countries.length > 0 && form.price && (
          <div className="rounded-lg bg-[var(--background)] border border-[var(--border)] p-3">
            <p className="text-sm text-[var(--muted)]">
              Will create{' '}
              <strong className="text-[var(--foreground)]">
                {PLAN_TYPE_LABELS[form.plan_type]} — {fmt(parseFloat(form.price))}
                {isIP ? '/IP/mo' : '/GB'}
              </strong>{' '}
              for{' '}
              <strong className="text-[var(--foreground)]">
                {form.countries.length} country(ies)
              </strong>
            </p>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={saving || form.countries.length === 0 || !form.price}
          className="w-full px-4 py-2.5 rounded-lg bg-[var(--primary)] text-white font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {saving ? 'Creating…' : `Create Product for ${form.countries.length} Country${form.countries.length !== 1 ? 'ies' : 'y'}`}
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────────
export default function PlanSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('settings');

  // Countries tab state
  const [countries, setCountries] = useState<CountryCPT[]>([]);
  const [countriesLoading, setCountriesLoading] = useState(true);
  const [savingTypes, setSavingTypes] = useState<Set<string>>(new Set());
  const [editTarget, setEditTarget] = useState<{
    country: CountryCPT; planType: string; enabled: boolean; currentPrice: number | null;
  } | null>(null);
  const [totalCountries, setTotalCountries] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Settings tab state
  const [planSettings, setPlanSettings] = useState<PlanSettingItem[]>([]);
  const [settingsLoading, setSettingsLoading] = useState(false);

  const fetchCountries = async () => {
    try {
      const res = await api.getAdminCountries();
      if (res.error) { setError('Failed: ' + res.error); return; }
      const data = res.data as any;
      setCountries(data?.countries ?? []);
      setTotalCountries(data?.total ?? 0);
    } catch { setError('Failed to load countries.'); }
    finally { setCountriesLoading(false); }
  };

  const fetchPlanSettings = async () => {
    setSettingsLoading(true);
    try {
      const res = await api.getPlanSettings();
      if (res.error) { setError('Settings: ' + res.error); return; }
      setPlanSettings((res.data ?? []) as unknown as PlanSettingItem[]);
    } catch { setError('Failed to load plan settings.'); }
    finally { setSettingsLoading(false); }
  };

  useEffect(() => { fetchCountries(); }, []);

  useEffect(() => {
    if (activeTab === 'settings' && planSettings.length === 0 && !settingsLoading) {
      fetchPlanSettings();
    }
  }, [activeTab]);

  const handleToggle = async (code: string, planType: string, current: boolean) => {
    const key = `${code}:${planType}`;
    setSavingTypes((prev) => new Set(prev).add(key));
    const res = await api.updateCountryPlanType(code, planType, { enabled: !current });
    if (res.error) setError(`${code} ${planType}: ${res.error}`);
    else {
      setCountries((prev) => prev.map((c) =>
        c.code !== code ? c : {
          ...c,
          enabled_plan_types: current
            ? c.enabled_plan_types.filter((t) => t !== planType)
            : [...c.enabled_plan_types, planType],
        }
      ));
    }
    setSavingTypes((prev) => { const n = new Set(prev); n.delete(key); return n; });
  };

  const openEdit = (country: CountryCPT, planType: string, currentPrice: number | null) => {
    setEditTarget({ country, planType, enabled: country.enabled_plan_types.includes(planType), currentPrice });
  };

  const handleSaveEdit = async (data: { enabled: boolean; price_per_gb: number | null; price_per_ip: number | null }) => {
    if (!editTarget) return;
    const { country, planType } = editTarget;
    setSavingTypes((prev) => new Set(prev).add(`${country.code}:${planType}`));
    const res = await api.updateCountryPlanType(country.code, planType, data);
    if (res.error) setError(`${country.code} ${planType}: ${res.error}`);
    else {
      setCountries((prev) => prev.map((c) =>
        c.code !== country.code ? c : {
          ...c,
          enabled_plan_types: data.enabled
            ? (c.enabled_plan_types.includes(planType) ? c.enabled_plan_types : [...c.enabled_plan_types, planType])
            : c.enabled_plan_types.filter((t) => t !== planType),
        }
      ));
      setEditTarget(null);
    }
    setSavingTypes((prev) => { const n = new Set(prev); n.delete(`${country.code}:${planType}`); return n; });
  };

  const sortedCountries = [...countries].sort((a, b) =>
    getCountryName(a.code).localeCompare(getCountryName(b.code))
  );

  return (
    <div className="space-y-6 px-4 md:px-0">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Plan Management</h1>
        <p className="text-[var(--muted)] text-sm">
          {activeTab === 'settings'
            ? 'Create products: pick type, set price, select countries'
            : 'Toggle countries per plan type and set per-country pricing'}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--card)] rounded-lg border border-[var(--border)] w-fit">
        <button
          onClick={() => setActiveTab('settings')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'settings' ? 'bg-[var(--primary)] text-white' : 'text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          Plan Settings
        </button>
        <button
          onClick={() => setActiveTab('countries')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'countries' ? 'bg-[var(--primary)] text-white' : 'text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          Countries
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">✕</button>
        </div>
      )}

      {/* ── Settings Tab: Product Builder ── */}
      {activeTab === 'settings' && (
        <div className="space-y-5">
          <ProductBuilder onCreated={fetchPlanSettings} />

          {/* Existing products overview */}
          {settingsLoading ? (
            <div className="flex items-center justify-center min-h-[200px]">
              <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : planSettings.length > 0 ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--border)]">
                <h2 className="text-sm font-medium text-[var(--muted)]">Existing Base Pricing</h2>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Proxy Type</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Model</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Base Price</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Country Overrides</th>
                  </tr>
                </thead>
                <tbody>
                  {planSettings.map((plan, idx) => {
                    const isIP = plan.base_pricing.pricing_model === 'per_IP';
                    const price = plan.base_pricing.price_per_ip ?? plan.base_pricing.price_per_gb ?? 0;
                    const overrides = Object.entries(plan.country_overrides);
                    return (
                      <tr key={plan.plan_type} className={`border-b border-[var(--border)] ${idx % 2 === 0 ? 'bg-[var(--card)]' : 'bg-[var(--background)]'}`}>
                        <td className="px-4 py-3 text-[var(--foreground)]">{PLAN_TYPE_LABELS[plan.plan_type] ?? plan.plan_type}</td>
                        <td className="px-4 py-3 text-[var(--foreground)]">{isIP ? 'per IP' : 'per GB'}</td>
                        <td className="px-4 py-3 text-[var(--foreground)]">{fmt(price)}{!isIP && '/GB'}</td>
                        <td className="px-4 py-3">
                          {overrides.length === 0 ? (
                            <span className="text-[var(--muted)]">—</span>
                          ) : (
                            <div className="flex flex-wrap gap-1">
                              {overrides.map(([c, p]) => (
                                <span key={c} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-[var(--background)] border border-[var(--border)]">
                                  {c} {fmt(p)}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}

      {/* ── Countries Tab ── */}
      {activeTab === 'countries' && (
        countriesLoading ? (
          <div className="flex items-center justify-center min-h-[300px]">
            <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[700px]">
                  <thead>
                    <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                      <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Country</th>
                      {PLAN_TYPE_ORDER.map((type) => (
                        <th key={type} className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">
                          {PLAN_TYPE_LABELS[type]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedCountries.map((country) => (
                      <CountryRow
                        key={country.code}
                        country={country}
                        onToggle={handleToggle}
                        onEditPrice={(pt, price) => openEdit(country, pt, price)}
                        savingTypes={savingTypes}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-3 border-t border-[var(--border)] text-sm text-[var(--muted)]">
                Showing {countries.length} of {totalCountries} countries
              </div>
            </div>

            {editTarget && (
              <EditModal
                country={editTarget.country}
                planType={editTarget.planType}
                enabled={editTarget.enabled}
                currentPrice={editTarget.currentPrice}
                onSave={handleSaveEdit}
                onClose={() => setEditTarget(null)}
                saving={savingTypes.has(`${editTarget.country.code}:${editTarget.planType}`)}
              />
            )}
          </>
        )
      )}
    </div>
  );
}
