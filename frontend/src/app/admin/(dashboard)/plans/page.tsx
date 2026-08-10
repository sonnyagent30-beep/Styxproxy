'use client';

import { useState, useEffect, useMemo } from 'react';
import api from '@/lib/api';
import { COUNTRIES } from '@/lib/products';
import type { CountryCPT } from '@/types';

// ─── Constants ────────────────────────────────────────────────────────────────

type Tab = 'settings' | 'countries';

const PLAN_TYPE_ORDER = ['dc', 'isp', 'residential', 'mobile'] as const;
const PLAN_TYPE_LABELS: Record<string, string> = {
  dc: 'Datacenter',
  isp: 'ISP Proxies',
  residential: 'Residential',
  mobile: 'Mobile 4G',
};

const fmt = (n: number) =>
  new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 }).format(n);

function getCountryFlag(code: string) {
  return COUNTRIES[code]?.flag ?? '🌍';
}
function getCountryName(code: string) {
  return COUNTRIES[code]?.name ?? code;
}

// ─── Country Row ──────────────────────────────────────────────────────────────

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
        const ptStatus = country.plan_types?.[type];
        const currentPrice = ptStatus
          ? (type === 'dc' || type === 'isp' ? ptStatus.price_per_ip : ptStatus.price_per_gb)
          : null;

        return (
          <td key={type} className="px-4 py-3 text-center">
            <div className="flex flex-col items-center gap-1">
              {/* Toggle */}
              <button
                onClick={() => !saving && onToggle(type, !isEnabled)}
                disabled={saving}
                title={isEnabled ? 'Disable' : 'Enable'}
                className={`relative w-10 h-5 rounded-full transition-colors disabled:opacity-40 ${
                  isEnabled ? 'bg-green-500' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                    isEnabled ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>

              {/* Price badge */}
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

// ─── Edit Modal ───────────────────────────────────────────────────────────────

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
  const isIP = planType === 'dc' || planType === 'isp';
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
        <p className="text-sm text-[var(--muted)] mb-5 capitalize">
          {PLAN_TYPE_LABELS[planType] ?? planType} Pricing
        </p>

        {/* Enable toggle */}
        <label className="flex items-center gap-3 mb-4 cursor-pointer select-none">
          <div
            onClick={() => setIsEnabled(!isEnabled)}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              isEnabled ? 'bg-green-500' : 'bg-gray-600'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                isEnabled ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </div>
          <span className="text-sm text-[var(--foreground)]">
            {isEnabled ? 'Enabled' : 'Disabled'}
          </span>
        </label>

        {/* Price */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-[var(--muted)] mb-2">
            Price per {isIP ? 'IP/month (₦)' : 'GB (₦)'}
          </label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder={isIP ? 'e.g. 8000' : 'e.g. 3000'}
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] disabled:opacity-40"
            disabled={!isEnabled}
          />
          {price && !isNaN(parsed) && (
            <p className="text-xs text-[var(--muted)] mt-1">
              {isIP
                ? `${fmt(parsed)} per IP/month`
                : `${fmt(parsed)} per GB`}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--background)]"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || (isEnabled && !price)}
            className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function PlanSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('countries');
  const [countries, setCountries] = useState<CountryCPT[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingTypes, setSavingTypes] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [editTarget, setEditTarget] = useState<{
    country: CountryCPT;
    planType: string;
    enabled: boolean;
    currentPrice: number | null;
  } | null>(null);

  const fetchCountries = async () => {
    try {
      const res = await api.getAdminCountries();
      if (res.error) {
        setError('Failed to load: ' + res.error);
        return;
      }
      setCountries(res.data?.countries ?? []);
      setTotal(res.data?.total ?? 0);
    } catch {
      setError('Failed to load countries. Refresh the page.');
    }
  };

  useEffect(() => {
    if (activeTab === 'countries') {
      setLoading(true);
      fetchCountries().finally(() => setLoading(false));
    }
  }, [activeTab]);

  const handleToggle = async (countryCode: string, planType: string, enabled: boolean) => {
    const key = `${countryCode}:${planType}`;
    setSavingTypes((s) => new Set(s).add(key));
    try {
      await api.updateCountryPlanType(countryCode, planType, { enabled });
      setCountries((prev) =>
        prev.map((c) => {
          if (c.code !== countryCode) return c;
          const current = new Set(c.enabled_plan_types || []);
          enabled ? current.add(planType) : current.delete(planType);
          return { ...c, enabled_plan_types: Array.from(current) };
        })
      );
    } catch (err: any) {
      setError(err.message || 'Update failed');
    } finally {
      setSavingTypes((s) => {
        const next = new Set(s);
        next.delete(key);
        return next;
      });
    }
  };

  const handleSaveEdit = async (data: {
    enabled: boolean;
    price_per_gb: number | null;
    price_per_ip: number | null;
  }) => {
    if (!editTarget) return;
    const { country, planType } = editTarget;
    setSaving(true);
    try {
      await api.updateCountryPlanType(country.code, planType, data);
      setCountries((prev) =>
        prev.map((c) => {
          if (c.code !== country.code) return c;
          const current = new Set(c.enabled_plan_types || []);
          data.enabled ? current.add(planType) : current.delete(planType);
          const updatedPt = {
            plan_type: planType,
            enabled: data.enabled,
            price_per_gb: data.price_per_gb,
            price_per_ip: data.price_per_ip,
            provider_id: c.plan_types?.[planType]?.provider_id ?? null,
          };
          return {
            ...c,
            enabled_plan_types: Array.from(current),
            plan_types: { ...(c.plan_types || {}), [planType]: updatedPt },
          };
        })
      );
      setEditTarget(null);
    } catch (err: any) {
      setError(err.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (country: CountryCPT, planType: string, currentPrice: number | null) => {
    const isEnabled = (country.enabled_plan_types || []).includes(planType);
    setEditTarget({ country, planType, enabled: isEnabled, currentPrice });
  };

  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const c of countries) {
      for (const pt of c.enabled_plan_types || []) {
        counts[pt] = (counts[pt] || 0) + 1;
      }
    }
    return counts;
  }, [countries]);

  return (
    <div className="space-y-6 px-4 md:px-0">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Country Management</h1>
        <p className="text-[var(--muted)]">Enable/disable countries and set pricing per plan type</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {PLAN_TYPE_ORDER.map((type) => (
          <div key={type} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-3">
            <div className="text-xs text-[var(--muted)] uppercase tracking-wide">{PLAN_TYPE_LABELS[type]}</div>
            <div className="text-2xl font-bold text-[var(--foreground)]">{stats[type] ?? 0}</div>
            <div className="text-xs text-[var(--muted)]">countries enabled</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--card)] rounded-lg border border-[var(--border)] w-fit">
        <button
          onClick={() => setActiveTab('settings')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'settings'
              ? 'bg-[var(--primary)] text-white'
              : 'text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          Plan Settings
        </button>
        <button
          onClick={() => setActiveTab('countries')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'countries'
              ? 'bg-[var(--primary)] text-white'
              : 'text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          Countries
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">✕</button>
        </div>
      )}

      {activeTab === 'countries' ? (
        loading ? (
          <div className="flex items-center justify-center min-h-[400px]">
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
                    {countries
                      .sort((a, b) =>
                        (COUNTRIES[a.code]?.name ?? a.code).localeCompare(COUNTRIES[b.code]?.name ?? b.code)
                      )
                      .map((country) => (
                        <CountryRow
                          key={country.code}
                          country={country}
                          onToggle={(pt, enabled) => handleToggle(country.code, pt, enabled)}
                          onEditPrice={(pt, price) => openEdit(country, pt, price)}
                          savingTypes={savingTypes}
                        />
                      ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-3 border-t border-[var(--border)] text-sm text-[var(--muted)]">
                Showing {countries.length} of {total} countries
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
                saving={saving}
              />
            )}
          </>
        )
      ) : (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-8 text-center text-[var(--muted)]">
          Plan Settings (base pricing per plan type) — legacy. Use the <strong>Countries</strong> tab above for per-country pricing.
        </div>
      )}
    </div>
  );
}
