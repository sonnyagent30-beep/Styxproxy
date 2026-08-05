'use client';

import { useState, useEffect, useMemo } from 'react';
import api from '@/lib/api';
import { COUNTRIES } from '@/lib/products';
import type { Plan, PlanSetting } from '@/types';

// ─── Types ──────────────────────────────────────────────────────────────────

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

type Tab = 'settings' | 'countries';

interface PlanWithType extends Plan {
  plan_type_key: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const PLAN_TYPE_LABELS: Record<string, string> = {
  datacenter: 'Datacenter',
  mobile: 'Mobile 4G',
  residential: 'Residential',
  isp: 'ISP Proxies',
};

const PLAN_TYPE_KEYS = ['datacenter', 'mobile', 'residential', 'isp'] as const;

function getCountryFlag(code: string) {
  return COUNTRIES[code]?.flag ?? '🌍';
}

function getCountryName(code: string) {
  return COUNTRIES[code]?.name ?? code;
}

const fmt = (n: number) =>
  new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 }).format(n);

// ─── Main Component ──────────────────────────────────────────────────────────

export default function PlanSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('settings');
  const [planSettings, setPlanSettings] = useState<PlanSettingItem[]>([]);
  const [plans, setPlans] = useState<PlanWithType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingPlan, setEditingPlan] = useState<PlanSettingItem | null>(null);
  const [editForm, setEditForm] = useState({
    basePrice: '',
    overrides: [] as { country: string; price: string }[],
  });

  // Fetch plan settings
  const fetchPlanSettings = async () => {
    try {
      const res = await api.getPlanSettings();
      if (res.error) {
        setError('Failed to load plan settings: ' + res.error);
        return;
      }
      setPlanSettings((res.data ?? []) as unknown as PlanSettingItem[]);
    } catch (err) {
      console.error('Failed to fetch plan settings:', err);
      setError('Failed to load plan settings. Please refresh.');
    }
  };

  // Fetch all plans (paginate through all — BE limits to 100/page)
  const fetchPlans = async () => {
    try {
      let allPlans: PlanWithType[] = [];
      let page = 1;
      let hasNext = true;
      while (hasNext && page <= 5) {
        const res = await api.getPlans(page, 100);
        if (res.error || !res.data) break;
        const planList: Plan[] = res.data.data ?? [];
        allPlans = allPlans.concat(
          planList.map((p) => ({
            ...p,
            plan_type_key: String(p.plan_type).toLowerCase(),
          }))
        );
        hasNext = res.data.pagination?.has_next ?? false;
        page++;
      }
      setPlans(allPlans);
    } catch (err) {
      console.error('Failed to fetch plans:', err);
      setError('Failed to load plans. Please refresh.');
    }
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      await Promise.all([fetchPlanSettings(), fetchPlans()]);
      setLoading(false);
    };
    load();
  }, []);

  // Build country toggle state
  const countryToggleState = useMemo(() => {
    const state: Record<string, Record<string, boolean>> = {};
    for (const country of Object.keys(COUNTRIES)) {
      state[country] = {};
      for (const type of PLAN_TYPE_KEYS) {
        const plan = plans.find(
          (p) => p.country === country && p.plan_type_key === type
        );
        state[country][type] = plan?.is_active ?? false;
      }
    }
    return state;
  }, [plans]);

  // Handle toggle
  const handleToggle = async (country: string, type: string, current: boolean) => {
    const plan = plans.find(
      (p) => p.country === country && p.plan_type_key === type
    );
    if (!plan) return;

    setSaving(true);
    try {
      await api.updatePlan(plan.id, { is_active: !current });
      await fetchPlans();
    } catch (err) {
      setError(`Failed to toggle ${getCountryName(country)} ${type}`);
    } finally {
      setSaving(false);
    }
  };

  // Open edit modal
  const openEdit = (plan: PlanSettingItem) => {
    const price =
      plan.base_pricing.price_per_ip ?? plan.base_pricing.price_per_gb ?? 0;
    const overrides = Object.entries(plan.country_overrides).map(
      ([country, price]) => ({
        country,
        price: String(price),
      })
    );
    setEditForm({
      basePrice: String(price),
      overrides,
    });
    setEditingPlan(plan);
  };

  // Helper to call admin API directly
  const adminFetch = async (endpoint: string, options: RequestInit = {}) => {
    const token = api.getAdminToken();
    const res = await fetch(`/api${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  };

  // Save plan setting
  const handleSave = async () => {
    if (!editingPlan) return;
    setSaving(true);
    setError(null);

    try {
      const isIP = editingPlan.base_pricing.pricing_model === 'per_IP';
      const basePrice = parseInt(editForm.basePrice, 10);

      // Update base pricing
      await adminFetch(`/admin/plan-settings/${editingPlan.plan_type}`, {
        method: 'PATCH',
        body: JSON.stringify({
          setting_value: {
            ...editingPlan.base_pricing,
            price_per_ip: isIP ? basePrice : null,
            price_per_gb: isIP ? null : basePrice,
          },
        }),
      });

      // Update country overrides for ISP
      if (editingPlan.plan_type === 'isp') {
        const overrideObj: Record<string, number> = {};
        for (const ov of editForm.overrides) {
          if (ov.country && ov.price) {
            overrideObj[ov.country.toUpperCase()] = parseInt(ov.price, 10);
          }
        }
        await adminFetch(`/admin/plan-settings/${editingPlan.plan_type}`, {
          method: 'PATCH',
          body: JSON.stringify({
            setting_value: {
              country_overrides: overrideObj,
            },
          }),
        });
      }

      await fetchPlanSettings();
      setEditingPlan(null);
    } catch (err) {
      setError('Failed to save plan settings');
    } finally {
      setSaving(false);
    }
  };

  // Add override row
  const addOverride = () => {
    setEditForm((prev) => ({
      ...prev,
      overrides: [...prev.overrides, { country: '', price: '' }],
    }));
  };

  // Remove override row
  const removeOverride = (idx: number) => {
    setEditForm((prev) => ({
      ...prev,
      overrides: prev.overrides.filter((_, i) => i !== idx),
    }));
  };

  const sortedCountries = useMemo(
    () =>
      Object.entries(COUNTRIES).sort(([, a], [, b]) => a.name.localeCompare(b.name)),
    []
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 px-4 md:px-0">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Plan Management</h1>
        <p className="text-[var(--muted)]">Configure plan pricing and country availability</p>
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
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm">
          {error}
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'settings' && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Proxy Type</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Pricing Model</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Base Price</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Country Overrides</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-[var(--muted)]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {planSettings && planSettings.length > 0 ? planSettings.map((plan, idx) => {
                const label = PLAN_TYPE_LABELS[plan.plan_type] ?? plan.plan_type;
                const isIP = plan.base_pricing.pricing_model === 'per_IP';
                const price = plan.base_pricing.price_per_ip ?? plan.base_pricing.price_per_gb ?? 0;
                const overrideCount = Object.keys(plan.country_overrides).length;

                return (
                  <tr
                    key={plan.plan_type}
                    className={`border-b border-[var(--border)] ${
                      idx % 2 === 0 ? 'bg-[var(--card)]' : 'bg-[var(--background)]'
                    }`}
                  >
                    <td className="px-4 py-3 text-[var(--foreground)]">{label}</td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{isIP ? 'per IP' : 'per GB'}</td>
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {fmt(price)}
                      {!isIP && '/GB'}
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {overrideCount === 0 ? (
                        '—'
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(plan.country_overrides).map(([c, p]) => (
                            <span
                              key={c}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-[var(--background)] border border-[var(--border)]"
                            >
                              {c} {fmt(p)}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => openEdit(plan)}
                        className="px-3 py-1.5 text-sm rounded-md bg-[var(--primary)] text-white hover:opacity-90 transition-opacity"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                );
              }) : (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted)]">
                    No plan settings found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'countries' && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px]">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                  <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Country</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">DC</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">ISP</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">Mobile</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">Residential</th>
                </tr>
              </thead>
              <tbody>
                {sortedCountries.map(([code, info], idx) => (
                  <tr
                    key={code}
                    className={`border-b border-[var(--border)] ${
                      idx % 2 === 0 ? 'bg-[var(--card)]' : 'bg-[var(--background)]'
                    }`}
                  >
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {info.flag} {info.name}
                    </td>
                    {PLAN_TYPE_KEYS.map((type) => {
                      const isOn = countryToggleState[code]?.[type] ?? false;
                      return (
                        <td key={type} className="px-4 py-3 text-center">
                          <button
                            onClick={() => !saving && handleToggle(code, type, isOn)}
                            disabled={saving}
                            className={`relative w-11 h-6 rounded-full transition-colors ${
                              isOn ? 'bg-green-500' : 'bg-gray-600'
                            } disabled:opacity-50`}
                          >
                            <span
                              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                                isOn ? 'translate-x-5' : 'translate-x-0'
                              }`}
                            />
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setEditingPlan(null)}
          />
          <div className="relative z-10 w-full max-w-md p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl">
            <h2 className="text-lg font-bold text-[var(--foreground)] mb-4">
              Edit {PLAN_TYPE_LABELS[editingPlan.plan_type] ?? editingPlan.plan_type}
            </h2>

            {/* Base Price */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-[var(--muted)] mb-2">
                Base Price (₦)
              </label>
              <input
                type="number"
                value={editForm.basePrice}
                onChange={(e) => setEditForm((prev) => ({ ...prev, basePrice: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
              />
            </div>

            {/* Country Overrides (ISP only) */}
            {editingPlan.plan_type === 'isp' && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-[var(--muted)]">
                    Country Overrides
                  </label>
                  <button
                    type="button"
                    onClick={addOverride}
                    className="text-sm text-[var(--primary)] hover:underline"
                  >
                    + Add
                  </button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {editForm.overrides.map((ov, idx) => (
                    <div key={idx} className="flex gap-2 items-center">
                      <input
                        type="text"
                        placeholder="Country code (e.g. GB)"
                        value={ov.country}
                        onChange={(e) => {
                          const val = e.target.value.toUpperCase().slice(0, 2);
                          const newOverrides = [...editForm.overrides];
                          newOverrides[idx] = { ...ov, country: val };
                          setEditForm((prev) => ({ ...prev, overrides: newOverrides }));
                        }}
                        className="flex-1 px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
                      />
                      <input
                        type="number"
                        placeholder="Price"
                        value={ov.price}
                        onChange={(e) => {
                          const newOverrides = [...editForm.overrides];
                          newOverrides[idx] = { ...ov, price: e.target.value };
                          setEditForm((prev) => ({ ...prev, overrides: newOverrides }));
                        }}
                        className="w-24 px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
                      />
                      <button
                        type="button"
                        onClick={() => removeOverride(idx)}
                        className="text-red-400 hover:text-red-300"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setEditingPlan(null)}
                className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--background)]"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
