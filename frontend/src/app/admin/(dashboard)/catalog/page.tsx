
/* eslint-disable react-hooks/set-state-in-effect */

'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { Plan } from '@/types';

// All supported countries with display info
const ALL_COUNTRIES = [
  { code: 'US', name: 'United States', flag: '🇺🇸' },
  { code: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
  { code: 'DE', name: 'Germany', flag: '🇩🇪' },
  { code: 'CA', name: 'Canada', flag: '🇨🇦' },
  { code: 'AU', name: 'Australia', flag: '🇦🇺' },
  { code: 'FR', name: 'France', flag: '🇫🇷' },
  { code: 'BR', name: 'Brazil', flag: '🇧🇷' },
  { code: 'IN', name: 'India', flag: '🇮🇳' },
  { code: 'JP', name: 'Japan', flag: '🇯🇵' },
  { code: 'SG', name: 'Singapore', flag: '🇸🇬' },
  { code: 'KR', name: 'South Korea', flag: '🇰🇷' },
  { code: 'NL', name: 'Netherlands', flag: '🇳🇱' },
  { code: 'SE', name: 'Sweden', flag: '🇸🇪' },
  { code: 'CH', name: 'Switzerland', flag: '🇨🇭' },
  { code: 'IT', name: 'Italy', flag: '🇮🇹' },
  { code: 'ES', name: 'Spain', flag: '🇪🇸' },
  { code: 'MX', name: 'Mexico', flag: '🇲🇽' },
  { code: 'ZA', name: 'South Africa', flag: '🇿🇦' },
  { code: 'NG', name: 'Nigeria', flag: '🇳🇬' },
  { code: 'AE', name: 'UAE', flag: '🇦🇪' },
  { code: 'EG', name: 'Egypt', flag: '🇪🇬' },
];

type PlanType = 'residential' | 'datacenter' | 'mobile' | 'isp';

const PLAN_META: Record<PlanType, { label: string; description: string; color: string }> = {
  residential: {
    label: 'Residential',
    description: 'Real home IPs — highest success rate for sneaker sites, social media, scraping',
    color: 'bg-green-500/20 text-green-400 border-green-500/30',
  },
  datacenter: {
    label: 'Datacenter',
    description: 'Fast cloud server IPs — budget bulk use, speed-critical automation',
    color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  },
  mobile: {
    label: 'Mobile 4G',
    description: 'Carrier-grade IPs — best for mobile-only platforms and ad verification',
    color: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  },
  isp: {
    label: 'ISP Proxies',
    description: 'Fast ISP IPs — static addresses, good for social accounts and multi-login',
    color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  },
};

interface PlanGroup {
  plan_type: PlanType;
  plans: Plan[];
}

export default function AdminCatalogPage() {
  const [planGroups, setPlanGroups] = useState<PlanGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Track active/inactive state per plan id
  const [activeMap, setActiveMap] = useState<Record<number, boolean>>({});

  const loadPlans = useCallback(async () => {
    setLoading(true);
    setError('');
    // Fetch all plans across pages (104 total > 100 per page)
    let page = 1;
    let allPlans: Plan[] = [];
    while (true) {
      const result = await api.getPlans(page, 100);
      if (result.error) { setError(result.error); break; }
      const plans: Plan[] = result.data?.data ?? [];
      allPlans = allPlans.concat(plans);
      if (!result.data?.pagination?.has_next) break;
      page++;
      if (page > 5) break; // safety cap
    }
    if (!allPlans.length && !error) {
      setPlanGroups([]);
    } else if (!error) {
      const grouped: Record<string, Plan[]> = {};
      for (const plan of allPlans) {
        const key = (plan.plan_type ?? 'unknown').toLowerCase();
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(plan);
      }
      const groups: PlanGroup[] = (['residential', 'datacenter', 'mobile', 'isp'] as PlanType[])
        .filter((k) => grouped[k]?.length > 0)
        .map((k) => ({ plan_type: k, plans: grouped[k] }));
      setPlanGroups(groups);

      // Init active map
      const map: Record<number, boolean> = {};
      for (const p of allPlans) map[p.id] = p.is_active ?? true;
      setActiveMap(map);
    }
    setLoading(false);
  }, [error]);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  const toggleCountry = (planId: number, enabled: boolean) => {
    setActiveMap((prev) => ({ ...prev, [planId]: enabled }));
    setSuccess('');
  };

  const hasChanges = (group: PlanGroup) =>
    group.plans.some((p) => activeMap[p.id] !== (p.is_active ?? true));

  const saveGroup = async (group: PlanGroup) => {
    const changedPlans = group.plans.filter((p) => activeMap[p.id] !== (p.is_active ?? true));
    if (!changedPlans.length) return;

    setSaving((prev) => ({ ...prev, [group.plan_type]: true }));
    setError('');
    setSuccess('');

    let ok = true;
    for (const plan of changedPlans) {
      const result = await api.updatePlan(plan.id, { is_active: activeMap[plan.id] });
      if (result.error) {
        setError(`Failed to update ${plan.plan_code}: ${result.error}`);
        ok = false;
        break;
      }
    }

    if (ok) {
      setSuccess(`${group.plan_type} countries updated — ${changedPlans.length} plan(s) changed`);
      loadPlans();
    }
    setSaving((prev) => ({ ...prev, [group.plan_type]: false }));
  };

  const saveAll = async () => {
    const changedGroups = planGroups.filter(hasChanges);
    if (!changedGroups.length) return;
    setError('');
    setSuccess('');
    for (const g of changedGroups) { await saveGroup(g); }
  };

  const anyChanges = planGroups.some(hasChanges);

  if (loading && planGroups.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Catalog Management</h1>
          <p className="text-[var(--muted)]">Manage available countries per plan type</p>
        </div>
        <div className="animate-pulse h-64 bg-[var(--card)] rounded-2xl border border-[var(--border)]" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Catalog Management</h1>
          <p className="text-[var(--muted)]">Enable or disable countries per proxy type — inactive plans are hidden from customers</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadPlans}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={saveAll}
            disabled={saving[planGroups[0]?.plan_type] || !anyChanges}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed text-sm"
          >
            {Object.values(saving).some(Boolean) ? (
              <><svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Saving...</>
            ) : 'Save All Changes'}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
          ✓ {success}
        </div>
      )}

      {/* Plan Groups */}
      <div className="grid gap-8">
        {planGroups.map((group) => {
          const meta = PLAN_META[group.plan_type] ?? { label: group.plan_type, description: '', color: 'bg-gray-500/20 text-gray-400' };
          const changed = hasChanges(group);
          const enabledCount = group.plans.filter((p) => activeMap[p.id]).length;

          return (
            <div key={group.plan_type} className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              {/* Group Header */}
              <div className="p-6 border-b border-[var(--border)]">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${meta.color}`}>
                      {meta.label}
                    </span>
                    <span className="text-[var(--muted)] text-sm">
                      {enabledCount}/{group.plans.length} countries enabled
                    </span>
                    {changed && (
                      <span className="px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                        Unsaved changes
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => saveGroup(group)}
                    disabled={saving[group.plan_type] || !changed}
                    className={`px-4 py-2 rounded-xl font-semibold text-sm transition-colors ${
                      changed
                        ? 'bg-[var(--primary)] text-black hover:opacity-90'
                        : 'bg-[var(--card-hover)] text-[var(--muted)] cursor-not-allowed'
                    } disabled:opacity-40`}
                  >
                    {saving[group.plan_type] ? 'Saving...' : changed ? 'Save Changes' : 'Saved'}
                  </button>
                </div>
                <p className="text-[var(--muted)] text-sm mt-2">{meta.description}</p>
              </div>

              {/* Country Cards */}
              <div className="p-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {group.plans.map((plan) => {
                    const country = ALL_COUNTRIES.find((c) => c.code === plan.country) ?? {
                      code: plan.country ?? '??',
                      name: plan.country ?? 'Unknown',
                      flag: '🌐',
                    };
                    const isActive = activeMap[plan.id] ?? true;
                    return (
                      <div
                        key={plan.id}
                        className={`relative rounded-xl border p-4 transition-all ${
                          isActive
                            ? 'bg-green-500/5 border-green-500/20'
                            : 'bg-[var(--card-hover)] border-[var(--border)] opacity-60'
                        }`}
                      >
                        {/* Toggle */}
                        <button
                          onClick={() => toggleCountry(plan.id, !isActive)}
                          className={`absolute top-3 right-3 w-10 h-6 rounded-full transition-colors ${
                            isActive ? 'bg-green-500' : 'bg-gray-600'
                          }`}
                          title={isActive ? 'Disable' : 'Enable'}
                        >
                          <span
                            className={`block w-4 h-4 mt-1 rounded-full bg-white shadow transition-transform ${
                              isActive ? 'translate-x-5' : 'translate-x-1'
                            }`}
                          />
                        </button>

                        <div className="flex items-start gap-2">
                          <span className="text-2xl">{country.flag}</span>
                          <div>
                            <p className="font-semibold text-sm">{country.name}</p>
                            <p className="text-xs text-[var(--muted)]">{plan.country}</p>
                            <p className="text-xs text-[var(--muted)] mt-1">
                              ₦{Number(plan.price_ngn).toLocaleString()} / {plan.duration_days}d
                            </p>
                            {plan.gb_tiers && plan.gb_tiers.length > 0 && (
                              <p className="text-xs text-[var(--muted)]">
                                {plan.gb_tiers[0]}–{plan.gb_tiers[plan.gb_tiers.length - 1]}GB
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="mt-2">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            isActive ? 'bg-green-500/20 text-green-400' : 'bg-gray-600/20 text-gray-400'
                          }`}>
                            {isActive ? '✓ Live' : '✗ Hidden'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Countries with no plan yet */}
                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs text-[var(--muted)] mb-2">Countries with no plan (add via /admin/plans):</p>
                  <div className="flex flex-wrap gap-2">
                    {ALL_COUNTRIES.filter(
                      (c) => !group.plans.some((p) => p.country === c.code)
                    ).map((c) => (
                      <span
                        key={c.code}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] text-xs text-[var(--muted)]"
                      >
                        <span>{c.flag}</span>
                        <span>{c.code}</span>
                        <span className="opacity-50">— no plan</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {planGroups.length === 0 && !loading && (
        <div className="text-center py-16 text-[var(--muted)]">
          <p>No plans found. Create plans via the /admin/plans page.</p>
        </div>
      )}
    </div>
  );
}
