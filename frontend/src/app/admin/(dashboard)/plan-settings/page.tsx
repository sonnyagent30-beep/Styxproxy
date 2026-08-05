'use client';

import { useState, useEffect, useMemo } from 'react';
import api from '@/lib/api';
import { COUNTRIES, type CountryInfo } from '@/lib/products';
import type { PlanSetting, PlanSettingValue } from '@/types';

const PLAN_TYPE_INFO: Record<string, { label: string; description: string; priceField: 'price_per_ip' | 'price_per_gb' }> = {
  ISP: { label: 'ISP Proxies', description: 'Internet Service Provider proxies with static IPs', priceField: 'price_per_ip' },
  DC: { label: 'Datacenter', description: 'Datacenter proxies for high-speed data center IPs', priceField: 'price_per_ip' },
  RESIDENTIAL: { label: 'Residential', description: 'Residential proxies using real home user IPs', priceField: 'price_per_gb' },
  MOBILE: { label: 'Mobile 4G', description: 'Mobile proxies using 4G/LTE carrier IPs', priceField: 'price_per_gb' },
};

const ALL_COUNTRIES: (CountryInfo & { code: string })[] = Object.entries(COUNTRIES).map(([code, info]) => ({
  code,
  ...info,
}));

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${
        checked ? 'bg-[#0AD25A]' : 'bg-[var(--border)]'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

function CountrySelector({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (countries: string[]) => void;
}) {
  const [search, setSearch] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const filteredCountries = useMemo(() => {
    if (!search) return ALL_COUNTRIES;
    const q = search.toLowerCase();
    return ALL_COUNTRIES.filter(
      (c) => c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
    );
  }, [search]);

  const selectedCountriesInfo = selected.map((code) => COUNTRIES[code]).filter(Boolean);

  const toggleCountry = (code: string) => {
    if (selected.includes(code)) {
      onChange(selected.filter((c) => c !== code));
    } else {
      onChange([...selected, code]);
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full min-h-[42px] px-3 py-2 text-left rounded-lg bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[#0AD25A] text-[var(--foreground)] flex items-center gap-2 flex-wrap"
      >
        {selected.length === 0 ? (
          <span className="text-[var(--muted)]">Select countries...</span>
        ) : (
          <>
            {selectedCountriesInfo.slice(0, 3).map((c) => (
              <span key={c?.code} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--primary)]/20 text-[var(--primary)] text-xs">
                {c?.flag} {c?.code}
              </span>
            ))}
            {selected.length > 3 && (
              <span className="text-xs text-[var(--muted)]">+{selected.length - 3} more</span>
            )}
          </>
        )}
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full max-h-64 overflow-auto rounded-lg bg-[var(--card)] border border-[var(--border)] shadow-lg">
          <div className="sticky top-0 p-2 border-b border-[var(--border)]">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search countries..."
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[#0AD25A] text-[var(--foreground)] placeholder:text-[var(--muted)] text-sm"
              autoFocus
            />
          </div>
          <div className="p-1">
            {filteredCountries.map((country) => (
              <label
                key={country.code}
                className="flex items-center gap-2 px-3 py-2 rounded hover:bg-[var(--card-hover)] cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(country.code)}
                  onChange={() => toggleCountry(country.code)}
                  className="rounded border-[var(--border)] text-[#0AD25A] focus:ring-[#0AD25A] bg-[var(--background)]"
                />
                <span>{country.flag}</span>
                <span className="text-sm">{country.name}</span>
                <span className="text-xs text-[var(--muted)] ml-auto">{country.code}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function GbTiersInput({
  value,
  onChange,
}: {
  value: string[];
  onChange: (tiers: string[]) => void;
}) {
  const [input, setInput] = useState(value.join(', '));

  const handleBlur = () => {
    const tiers = input
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t && !isNaN(Number(t)))
      .map((t) => String(Number(t)));
    const unique = [...new Set(tiers)].sort((a, b) => Number(a) - Number(b));
    onChange(unique);
    setInput(unique.join(', '));
  };

  return (
    <input
      type="text"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onBlur={handleBlur}
      placeholder="5, 10, 20, 50"
      className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[#0AD25A] text-[var(--foreground)] placeholder:text-[var(--muted)]"
    />
  );
}

function PlanCard({
  setting,
  onSave,
  saving,
}: {
  setting: PlanSetting;
  onSave: (data: Partial<PlanSetting>) => Promise<void>;
  saving: boolean;
}) {
  const info = PLAN_TYPE_INFO[setting.plan_type];
  const [localValue, setLocalValue] = useState<PlanSettingValue>(setting.setting_value);
  const [localActive, setLocalActive] = useState(setting.is_active);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const changed =
      JSON.stringify(localValue) !== JSON.stringify(setting.setting_value) ||
      localActive !== setting.is_active;
    setHasChanges(changed);
  }, [localValue, localActive, setting]);

  const handleSave = async () => {
    await onSave({
      setting_value: localValue,
      is_active: localActive,
    });
    setHasChanges(false);
  };

  const priceField = info.priceField;

  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 card-depth">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-[var(--foreground)]">{info.label}</h3>
          <p className="text-sm text-[var(--muted)]">{info.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-[var(--muted)]">Active</span>
          <ToggleSwitch
            checked={localActive}
            onChange={(v) => {
              setLocalActive(v);
              setHasChanges(true);
            }}
          />
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
            Price per {priceField === 'price_per_ip' ? 'IP' : 'GB'} (NGN)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={localValue[priceField] || 0}
            onChange={(e) => {
              setLocalValue({ ...localValue, [priceField]: Number(e.target.value) });
              setHasChanges(true);
            }}
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[#0AD25A] text-[var(--foreground)]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
            Available Countries
          </label>
          <CountrySelector
            selected={localValue.available_countries || []}
            onChange={(countries) => {
              setLocalValue({ ...localValue, available_countries: countries });
              setHasChanges(true);
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-[var(--foreground)]">Supports City</label>
          <ToggleSwitch
            checked={localValue.supports_city || false}
            onChange={(v) => {
              setLocalValue({ ...localValue, supports_city: v });
              setHasChanges(true);
            }}
          />
        </div>

        {priceField === 'price_per_gb' && (
          <div>
            <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
              GB Tiers (comma-separated)
            </label>
            <GbTiersInput
              value={localValue.gb_tiers || []}
              onChange={(tiers) => {
                setLocalValue({ ...localValue, gb_tiers: tiers });
                setHasChanges(true);
              }}
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
            Rotation Modes
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localValue.rotation_modes?.includes('rotating') || false}
                onChange={(e) => {
                  const modes = localValue.rotation_modes || [];
                  if (e.target.checked) {
                    setLocalValue({ ...localValue, rotation_modes: [...modes, 'rotating'] });
                  } else {
                    setLocalValue({ ...localValue, rotation_modes: modes.filter((m) => m !== 'rotating') });
                  }
                  setHasChanges(true);
                }}
                className="rounded border-[var(--border)] text-[#0AD25A] focus:ring-[#0AD25A] bg-[var(--background)]"
              />
              <span className="text-sm text-[var(--foreground)]">Rotating</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localValue.rotation_modes?.includes('static') || false}
                onChange={(e) => {
                  const modes = localValue.rotation_modes || [];
                  if (e.target.checked) {
                    setLocalValue({ ...localValue, rotation_modes: [...modes, 'static'] });
                  } else {
                    setLocalValue({ ...localValue, rotation_modes: modes.filter((m) => m !== 'static') });
                  }
                  setHasChanges(true);
                }}
                className="rounded border-[var(--border)] text-[#0AD25A] focus:ring-[#0AD25A] bg-[var(--background)]"
              />
              <span className="text-sm text-[var(--foreground)]">Static</span>
            </label>
          </div>
        </div>

        {hasChanges && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-2.5 px-4 rounded-xl bg-[#0AD25A] text-black font-semibold hover:bg-[#0AD25A]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {saving ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Saving...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Save Changes
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default function PlanSettingsPage() {
  const [settings, setSettings] = useState<PlanSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingMap, setSavingMap] = useState<Record<number, boolean>>({});
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getPlanSettings();
      if (result.data) {
        setSettings(result.data.settings);
      } else {
        setError(result.error || 'Failed to load plan settings');
      }
    } catch (err) {
      setError('Failed to load plan settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (id: number, data: Partial<PlanSetting>) => {
    setSavingMap((prev) => ({ ...prev, [id]: true }));
    setSuccessMsg(null);

    const setting = settings.find((s) => s.id === id);
    if (!setting) return;

    try {
      const result = await api.updatePlanSettings(id, {
        plan_type: setting.plan_type,
        setting_value: {
          price_per_gb: data.setting_value?.price_per_gb,
          price_per_ip: data.setting_value?.price_per_ip,
          available_countries: data.setting_value?.available_countries || [],
          gb_tiers: data.setting_value?.gb_tiers,
          supports_city: data.setting_value?.supports_city || false,
          rotation_modes: data.setting_value?.rotation_modes || [],
        },
        is_active: data.is_active ?? setting.is_active,
      });

      if (result.data) {
        setSettings((prev) =>
          prev.map((s) => (s.id === id ? result.data! : s))
        );
        setSuccessMsg(`${PLAN_TYPE_INFO[setting.plan_type]?.label || setting.plan_type} settings saved`);
        setTimeout(() => setSuccessMsg(null), 3000);
      } else {
        setError(result.error || 'Failed to save settings');
      }
    } catch (err) {
      setError('Failed to save settings');
    } finally {
      setSavingMap((prev) => ({ ...prev, [id]: false }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-pulse text-[var(--muted)]">Loading plan settings...</div>
      </div>
    );
  }

  if (error && settings.length === 0) {
    return (
      <div className="bg-[var(--card)] border border-red-500/30 rounded-2xl p-6">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Plan Settings</h1>
          <p className="text-sm text-[var(--muted)]">Configure pricing and availability for each plan type</p>
        </div>
      </div>

      {successMsg && (
        <div className="bg-[#0AD25A]/20 border border-[#0AD25A]/30 rounded-xl p-4 text-[#0AD25A] flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {successMsg}
        </div>
      )}

      {error && (
        <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-4 text-red-400">
          {error}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {settings.map((setting) => (
          <PlanCard
            key={setting.id}
            setting={setting}
            onSave={(data) => handleSave(setting.id, data)}
            saving={savingMap[setting.id] || false}
          />
        ))}
      </div>
    </div>
  );
}
