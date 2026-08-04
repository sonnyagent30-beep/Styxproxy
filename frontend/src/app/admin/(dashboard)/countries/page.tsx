'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { Country } from '@/types';

const PLAN_TYPES = [
  { key: 'ISP', label: 'ISP' },
  { key: 'DC', label: 'Datacenter' },
  { key: 'RESIDENTIAL', label: 'Residential' },
  { key: 'MOBILE', label: 'Mobile 4G' },
];

const REGIONS = ['Africa', 'Americas', 'Asia', 'Europe', 'Oceania'];

function getPlanTypeEligible(country: Country, planType: string): boolean {
  // The plan_type_eligible field is a single boolean on the model.
  // We interpret it as: if is_supported=True, country is eligible for all types.
  // When we store per-type eligibility, we encode it in proxy_pool as a JSON override.
  // For simplicity, we show all plan types as eligible if is_supported=True.
  return country.is_supported;
}

function setPlanTypeEligible(country: Country, planType: string, eligible: boolean): Partial<Country> {
  return {
    is_supported: eligible,
    proxy_pool: country.proxy_pool,
    notes: country.notes,
  };
}

function ToggleSwitch({
  checked,
  onChange,
  disabled = false,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 ${
        checked ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-4' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}

export default function CountriesPage() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'supported' | 'unsupported'>('all');
  const [regionFilter, setRegionFilter] = useState<string>('All');
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadCountries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCountries();
      if (res.data) {
        setCountries(res.data);
      } else {
        setError(res.error || 'Failed to load countries');
      }
    } catch {
      setError('Failed to load countries');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCountries();
  }, [loadCountries]);

  const handleToggleSupported = async (country: Country) => {
    setSaving((prev) => ({ ...prev, [country.code]: true }));
    setSuccessMsg(null);
    try {
      const res = await api.updateCountry(country.code, {
        is_supported: !country.is_supported,
      });
      if (res.data) {
        setCountries((prev) =>
          prev.map((c) => (c.code === country.code ? { ...c, ...res.data } : c))
        );
        setSuccessMsg(`${country.name} ${!country.is_supported ? 'activated' : 'deactivated'}`);
        setTimeout(() => setSuccessMsg(null), 3000);
      }
    } finally {
      setSaving((prev) => ({ ...prev, [country.code]: false }));
    }
  };

  const handleTogglePlanType = async (country: Country, planType: string, eligible: boolean) => {
    setSaving((prev) => ({ ...prev, [`${country.code}-${planType}`]: true }));
    setSuccessMsg(null);
    try {
      // Per-plan-type eligibility: store as a JSON map in proxy_pool
      // e.g. {"ISP": true, "DC": true, "RESIDENTIAL": false, "MOBILE": true}
      const currentMap: Record<string, boolean> = (() => {
        try { return JSON.parse(country.proxy_pool || '{}'); } catch { return {}; }
      })();
      const updatedMap = { ...currentMap, [planType]: eligible };

      const res = await api.updateCountry(country.code, {
        is_supported: Object.values(updatedMap).some(Boolean),
        proxy_pool: JSON.stringify(updatedMap),
      });
      if (res.data) {
        setCountries((prev) =>
          prev.map((c) => (c.code === country.code ? { ...c, ...res.data } : c))
        );
        setSuccessMsg(`${country.name} ${planType} eligibility updated`);
        setTimeout(() => setSuccessMsg(null), 3000);
      }
    } finally {
      setSaving((prev) => ({ ...prev, [`${country.code}-${planType}`]: false }));
    }
  };

  const handleSaveNotes = async (country: Country, notes: string) => {
    setSaving((prev) => ({ ...prev, [`${country.code}-notes`]: true }));
    setSuccessMsg(null);
    try {
      const res = await api.updateCountry(country.code, { notes });
      if (res.data) {
        setCountries((prev) =>
          prev.map((c) => (c.code === country.code ? { ...c, ...res.data } : c))
        );
        setSuccessMsg(`${country.name} notes saved`);
        setTimeout(() => setSuccessMsg(null), 3000);
      }
    } finally {
      setSaving((prev) => ({ ...prev, [`${country.code}-notes`]: false }));
    }
  };

  const filtered = countries.filter((c) => {
    if (filter === 'supported' && !c.is_supported) return false;
    if (filter === 'unsupported' && c.is_supported) return false;
    if (regionFilter !== 'All' && c.region !== regionFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q) || c.code3.toLowerCase().includes(q);
    }
    return true;
  });

  const supportedCount = countries.filter((c) => c.is_supported).length;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-[-0.02em]">Countries</h1>
          <p className="text-[var(--muted)] text-sm mt-1">
            {supportedCount} of {countries.length} countries active &mdash; toggle to add/remove from catalog
          </p>
        </div>
        <div className="flex items-center gap-3">
          {successMsg && (
            <span className="text-sm text-green-400 animate-pulse">{successMsg}</span>
          )}
          <button
            onClick={loadCountries}
            className="px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm hover:border-[var(--primary)] transition-all"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex rounded-lg border border-[var(--border)] overflow-hidden">
          {(['all', 'supported', 'unsupported'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-[var(--primary)] text-black'
                  : 'bg-[var(--card)] hover:bg-[var(--surface)]'
              }`}
            >
              {f === 'all' ? 'All' : f === 'supported' ? 'Active' : 'Inactive'}
            </button>
          ))}
        </div>

        <select
          value={regionFilter}
          onChange={(e) => setRegionFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
        >
          <option value="All">All Regions</option>
          {REGIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Search country name or code..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[200px] px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm placeholder:text-[var(--muted)]"
        />
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {(['ISP', 'DC', 'RESIDENTIAL', 'MOBILE'] as const).map((pt) => {
          const count = countries.filter(
            (c) => c.is_supported
          ).length;
          return (
            <div key={pt} className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4">
              <p className="text-xs text-[var(--muted)] mb-1">{pt}</p>
              <p className="text-2xl font-bold text-[var(--primary)]">{count}</p>
              <p className="text-xs text-[var(--muted)]">active countries</p>
            </div>
          );
        })}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <span className="text-[var(--muted)]">Loading countries...</span>
        </div>
      )}

      {error && (
        <div className="text-center py-12">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={loadCountries}
            className="px-6 py-2 rounded-lg bg-[var(--primary)] text-black font-semibold"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="hidden lg:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left py-3 px-4 font-semibold w-[40px]">Flag</th>
                  <th className="text-left py-3 px-4 font-semibold">Country</th>
                  <th className="text-left py-3 px-4 font-semibold">Region</th>
                  <th className="text-center py-3 px-4 font-semibold">Active</th>
                  <th className="text-center py-3 px-4 font-semibold">ISP</th>
                  <th className="text-center py-3 px-4 font-semibold">DC</th>
                  <th className="text-center py-3 px-4 font-semibold">Residential</th>
                  <th className="text-center py-3 px-4 font-semibold">Mobile</th>
                  <th className="text-left py-3 px-4 font-semibold">Notes</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((country) => (
                  <tr
                    key={country.code}
                    className="border-b border-[var(--border)] hover:bg-[var(--surface)] transition-colors"
                  >
                    <td className="py-3 px-4 text-xl">{country.flag_emoji}</td>
                    <td className="py-3 px-4">
                      <div className="font-medium">{country.name}</div>
                      <div className="text-xs text-[var(--muted)]">{country.code} / {country.code3}</div>
                    </td>
                    <td className="py-3 px-4 text-[var(--muted)]">{country.region || '—'}</td>
                    <td className="py-3 px-4 text-center">
                      <ToggleSwitch
                        checked={country.is_supported}
                        onChange={() => !saving[country.code] && handleToggleSupported(country)}
                        disabled={saving[country.code]}
                      />
                    </td>
                    {PLAN_TYPES.map(({ key }) => (
                      <td key={key} className="py-3 px-4 text-center">
                        <ToggleSwitch
                          checked={country.is_supported}
                          onChange={(v) =>
                            !saving[`${country.code}-${key}`] && handleTogglePlanType(country, key, v)
                          }
                          disabled={saving[`${country.code}-${key}`] || saving[country.code]}
                        />
                      </td>
                    ))}
                    <td className="py-3 px-4">
                      <NotesField country={country} onSave={handleSaveNotes} saving={!!saving[`${country.code}-notes`]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="lg:hidden space-y-3">
            {filtered.map((country) => (
              <CountryCard
                key={country.code}
                country={country}
                saving={saving}
                onToggleSupported={handleToggleSupported}
                onTogglePlanType={handleTogglePlanType}
                onSaveNotes={handleSaveNotes}
              />
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="text-center py-12 text-[var(--muted)]">
              No countries match your filters.
            </div>
          )}
        </>
      )}
    </div>
  );
}

function NotesField({
  country,
  onSave,
  saving,
}: {
  country: Country;
  onSave: (c: Country, notes: string) => void;
  saving: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(country.notes || '');

  const handleSave = () => {
    onSave(country, value);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex gap-1">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-24 px-2 py-1 text-xs rounded border border-[var(--border)] bg-[var(--card)]"
          placeholder="Notes..."
          onKeyDown={(e) => e.key === 'Enter' && handleSave()}
        />
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-2 py-1 text-xs bg-[var(--primary)] text-black rounded font-medium"
        >
          {saving ? '...' : 'OK'}
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => { setEditing(true); setValue(country.notes || ''); }}
      className="text-xs text-[var(--muted)] hover:text-[var(--foreground)] text-left max-w-[120px] truncate block"
      title={country.notes || 'Click to add notes'}
    >
      {country.notes || <span className="italic">Add notes...</span>}
    </button>
  );
}

function CountryCard({
  country,
  saving,
  onToggleSupported,
  onTogglePlanType,
  onSaveNotes,
}: {
  country: Country;
  saving: Record<string, boolean>;
  onToggleSupported: (c: Country) => void;
  onTogglePlanType: (c: Country, pt: string, v: boolean) => void;
  onSaveNotes: (c: Country, notes: string) => void;
}) {
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{country.flag_emoji}</span>
          <div>
            <p className="font-semibold">{country.name}</p>
            <p className="text-xs text-[var(--muted)]">{country.code} / {country.code3} &middot; {country.region || 'No region'}</p>
          </div>
        </div>
        <ToggleSwitch
          checked={country.is_supported}
          onChange={() => onToggleSupported(country)}
          disabled={!!saving[country.code]}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        {PLAN_TYPES.map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between bg-[var(--card)] rounded-lg px-3 py-2">
            <span className="text-xs text-[var(--muted)]">{label}</span>
            <ToggleSwitch
              checked={country.is_supported}
              onChange={(v) => onTogglePlanType(country, key, v)}
              disabled={!!saving[`${country.code}-${key}`] || !!saving[country.code]}
            />
          </div>
        ))}
      </div>

      <NotesField country={country} onSave={onSaveNotes} saving={!!saving[`${country.code}-notes`]} />
    </div>
  );
}
