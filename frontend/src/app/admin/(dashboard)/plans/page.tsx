'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { COUNTRIES } from '@/lib/products';

// ─── Types ────────────────────────────────────────────────────────────────────
type Tab = 'settings' | 'countries';

interface CountryItem {
  code: string;
  name: string;
  flag_emoji: string;
  region: string;
  enabled_plan_types: string[];
  is_enabled: boolean;
}

interface ProductCard {
  plan_type: string;
  label: string;
  pricing_model: 'per_IP' | 'per_GB';
  base_price: number | null;
  countries: CountryPref[];
  is_active: boolean;
}

interface CountryPref {
  code: string;
  is_special: boolean; // true = special price, false = base price
  override_price: number | null; // the actual price
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const PRODUCTS = [
  { plan_type: 'DC', label: 'Datacenter', pricing_model: 'per_IP' as const },
  { plan_type: 'ISP', label: 'ISP Proxies', pricing_model: 'per_IP' as const },
  { plan_type: 'RESIDENTIAL', label: 'Residential', pricing_model: 'per_GB' as const },
  { plan_type: 'MOBILE', label: 'Mobile 4G', pricing_model: 'per_GB' as const },
];

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

// ─── Edit Product Modal ─────────────────────────────────────────────────────────
interface EditProductModalProps {
  product: ProductCard;
  allCountries: CountryItem[];
  onSaved: () => void;
  onClose: () => void;
}

function EditProductModal({ product, allCountries, onSaved, onClose }: EditProductModalProps) {
  const isIP = product.pricing_model === 'per_IP';
  const [basePrice, setBasePrice] = useState(String(product.base_price ?? ''));
  // baseCountries = countries in product using base price
  const [baseCountries, setBaseCountries] = useState<Set<string>>(
    new Set(product.countries.map((c) => c.code))
  );
  // specialCountries = Map<code, price> for countries with override (set per-item)
  const [specialCountries, setSpecialCountries] = useState<Map<string, number | null>>(new Map());

  const [isActive, setIsActive] = useState(product.is_active);
  const [saveStatus, setSaveStatus] = useState<Map<string, 'idle' | 'saving' | 'saved'>>(new Map());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCountryPicker, setShowCountryPicker] = useState(false);
  const [showSpecialPricePicker, setShowSpecialPricePicker] = useState(false);
  const [specialPriceSelection, setSpecialPriceSelection] = useState<Set<string>>(new Set());
  const [countrySearch, setCountrySearch] = useState('');
  // Track which countries were removed from base (via ✕ button) — saved on Save Changes
  const [removedCountries, setRemovedCountries] = useState<Set<string>>(new Set());  // Fetch is_special + price for ONLY countries that actually belong to this product
  // product.countries is the source of truth for which countries are in this product
  // GET /country/:code tells us if that country is base (is_special=false) or special (is_special=true)
  // Track whether we have fetched from API yet — prevents stale data overwrites
  const [pricesLoaded, setPricesLoaded] = useState(false);

  useEffect(() => {
    // Reset load flag when product changes (e.g. user closes and re-opens modal)
    setPricesLoaded(false);
    setRemovedCountries(new Set());
  }, [product.countries, product.plan_type]);

  useEffect(() => {
    // Skip if no countries or already loaded
    if (product.countries.length === 0) { setPricesLoaded(true); return; }
    if (pricesLoaded) return;

    // Use plan-settings endpoint which has base_pricing + country_overrides in one call
    api.getPlanSettings().then((res) => {
      if (res.error) { setPricesLoaded(true); return; }
      const allSettings: any[] = res.data ?? [];
      // Find the setting for this plan_type (normalize case)
      const planTypeUpper = product.plan_type.toUpperCase();
      const planTypeMap: Record<string, string> = { DC: 'datacenter', ISP: 'isp', RESIDENTIAL: 'residential', MOBILE: 'mobile' };
      const normalized = planTypeMap[planTypeUpper] ?? product.plan_type.toLowerCase();
      const setting = allSettings.find((s: any) => s.plan_type?.toLowerCase() === normalized);
      if (!setting) { setPricesLoaded(true); return; }

      const { base_pricing, country_overrides } = setting;
      const newSpecial = new Map<string, number | null>();
      const newBase = new Set<string>();

      // country_overrides: {GB: 9500, US: 8000} — these are the special countries
      const overrideCodes = new Set(Object.keys(country_overrides ?? {}));

      for (const c of product.countries) {
        if (overrideCodes.has(c.code)) {
          // This country has a special price
          newSpecial.set(c.code, country_overrides[c.code] ?? null);
        } else {
          // This country uses base price
          newBase.add(c.code);
        }
      }

      setSpecialCountries(newSpecial);
      setBaseCountries(newBase);

      // Set base price from plan-settings
      const bp = isIP ? base_pricing?.price_per_ip : base_pricing?.price_per_gb;
      if (bp) setBasePrice(String(bp));

      setPricesLoaded(true);
    });
  }, [product.countries, product.plan_type, pricesLoaded]);

  // Only show globally active countries in the picker ( Countries tab gate )
  const pickerCountries = allCountries.filter((c) => c.is_enabled);
  const filtered = pickerCountries.filter((c) =>
    getCountryName(c.code).toLowerCase().includes(countrySearch.toLowerCase()) ||
    c.code.toLowerCase().includes(countrySearch.toLowerCase())
  );

  // ─── LOCAL-STATE-ONLY toggles (no immediate API calls) ────────────────────────
  // All API writes happen ONLY from "Save Changes" button

  const toggleCountry = (code: string) => {
    const isAdding = !baseCountries.has(code) && !specialCountries.has(code);
    if (isAdding) {
      // Add to local base list — Save Changes will persist via createProductsBulk
      setBaseCountries((prev) => new Set([...prev, code]));
      setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
    } else {
      // Remove from local state — Save Changes will persist via removeCountryFromProduct
      setBaseCountries((prev) => { const n = new Set(prev); n.delete(code); return n; });
      setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
    }
  };

  // ─── Local-only: update special price in state (no auto-save) ──────────────────
  // Per-row Save button fires the actual API call

  const setOverride = (code: string, value: string) => {
    const num = value === '' ? null : parseFloat(value);
    if (num == null) {
      // Reset: move back to base (local state only — Save Changes will persist)
      setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
      setBaseCountries((prev) => new Set([...prev, code]));
    } else {
      // Set special price in local state
      setSpecialCountries((prev) => new Map(prev).set(code, num));
      setBaseCountries((prev) => { const n = new Set(prev); n.delete(code); return n; });
    }
  };

  // ✕ on base chip: local state only, Save Changes will remove from DB
  const handleRemoveCountry = (code: string) => {
    // If country was in base list, mark it as removed
    if (baseCountries.has(code)) {
      setRemovedCountries((prev) => new Set([...prev, code]));
    }
    setBaseCountries((prev) => { const n = new Set(prev); n.delete(code); return n; });
    setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
  };

  const handleSave = async () => {
    if (!basePrice || parseFloat(basePrice) <= 0) { setError('Enter a base price'); return; }
    setSaving(true);
    setError(null);

    try {
      // 1. Remove countries that were marked for removal
      const removed = [...removedCountries];
      for (const code of removed) {
        const res = await api.removeCountryFromProduct(code, product.plan_type);
        if (res.error) { setError('Failed to remove ' + code + ': ' + res.error); setSaving(false); return; }
      }

      // 2. Bulk create/update base countries
      const baseCodes = [...baseCountries];
      if (baseCodes.length > 0) {
        const res = await api.createProductsBulk({
          plan_type: product.plan_type,
          pricing_model: product.pricing_model,
          price: parseFloat(basePrice),
          countries: baseCodes,
          is_active: isActive,
        });
        if (res.error) { setError('Failed: ' + res.error); setSaving(false); return; }
      }

      // 3. Save each special country individually
      for (const [code, price] of specialCountries) {
        if (price == null || price <= 0) continue;
        const res = await api.updateCountryPlanType(code, product.plan_type, {
          enabled: true,
          is_special: true,
          price_per_ip: isIP ? price : undefined,
          price_per_gb: !isIP ? price : undefined,
        });
        if (res.error) { setError('Failed to save ' + code + ': ' + res.error); setSaving(false); return; }
      }
    } finally {
      setSaving(false);
    }

    onSaved();
    onClose();
  };

  const selectedCountries = allCountries.filter((c) => baseCountries.has(c.code) || specialCountries.has(c.code));
  const countriesWithOverrides = allCountries.filter((c) => specialCountries.has(c.code));
  const countriesWithBase = allCountries.filter((c) => baseCountries.has(c.code));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto py-8">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-2xl p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl my-4">
        <h2 className="text-lg font-bold text-[var(--foreground)] mb-1">Edit: {product.plan_type}</h2>
        <p className="text-sm text-[var(--muted)] mb-5">
          Set base price — then optionally set special prices for specific countries
        </p>

        {error && <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm">{error}</div>}

        {/* Base price */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-[var(--muted)] mb-2">
            Base Price (₦ {isIP ? 'per IP/month' : 'per GB'}) — used unless overridden below
          </label>
          <input
            type="number" min={1} step={100}
            value={basePrice}
            onChange={(e) => setBasePrice(e.target.value)}
            placeholder="e.g. 8000"
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
          />
        </div>

        {/* Active toggle */}
        <div className="mb-5 flex items-center gap-3">
          <div
            onClick={() => setIsActive(!isActive)}
            className={`relative w-11 h-6 rounded-full transition-colors cursor-pointer ${isActive ? 'bg-green-500' : 'bg-gray-600'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${isActive ? 'translate-x-5' : 'translate-x-0'}`} />
          </div>
          <span className="text-sm text-[var(--foreground)]">{isActive ? 'Active' : 'Inactive'}</span>
        </div>

        {/* Countries section */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-medium text-[var(--muted)]">
              Countries ({baseCountries.size + specialCountries.size} selected)
            </label>
            <button
              type="button"
              onClick={() => setShowCountryPicker((v) => !v)}
              className="text-sm text-[var(--primary)] hover:underline"
            >
              {showCountryPicker ? 'Done' : 'Add Countries'}
            </button>
            {(product.plan_type === 'DC' || product.plan_type === 'ISP') && (
              <button
                type="button"
                onClick={() => { setShowSpecialPricePicker(true); setSpecialPriceSelection(new Set()); }}
                className="text-sm text-yellow-400 hover:underline"
              >
                Set Special Price
              </button>
            )}
          </div>

          {showCountryPicker && (
            <div className="mb-4 border border-[var(--border)] rounded-lg bg-[var(--background)] overflow-hidden">
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
              <div className="max-h-48 overflow-y-auto divide-y divide-[var(--border)]">
                {filtered.length === 0 && (
                  <p className="p-3 text-sm text-[var(--muted)] text-center">
                    No active countries — enable countries in the Countries tab first
                  </p>
                )}
                {filtered.map((c) => {
                  const selected = baseCountries.has(c.code) || specialCountries.has(c.code);
                  return (
                    <label
                      key={c.code}
                      className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-[var(--card)] transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleCountry(c.code)}
                        className="w-4 h-4 rounded accent-[var(--primary)]"
                      />
                      <span className="text-lg">{c.flag_emoji}</span>
                      <div>
                        <div className="text-sm text-[var(--foreground)]">{c.name}</div>
                        <div className="text-xs text-[var(--muted)]">{c.code}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Special Price Picker — DC/ISP only */}
          {showSpecialPricePicker && (
            <div className="mb-4 border-2 border-yellow-500/40 rounded-lg bg-yellow-500/5 overflow-hidden">
              <div className="p-3 border-b border-yellow-500/20 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-yellow-400">Set Special Price</p>
                  <p className="text-xs text-[var(--muted)] mt-0.5">
                    Select countries to set individual special prices, then click Done
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowSpecialPricePicker(false)}
                    className="px-3 py-1 rounded text-xs border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
                  >Cancel</button>
                  <button
                    onClick={() => {
                      // Local state only — Save Changes will persist all changes
                      const toMove = [...specialPriceSelection];
                      setSpecialCountries((prev) => {
                        const n = new Map(prev);
                        for (const code of toMove) n.set(code, null);
                        return n;
                      });
                      setBaseCountries((prev) => {
                        const n = new Set(prev);
                        for (const code of toMove) n.delete(code);
                        return n;
                      });
                      setSpecialPriceSelection(new Set());
                      setShowSpecialPricePicker(false);
                    }}
                    className="px-3 py-1 rounded text-xs bg-yellow-500 text-black font-medium hover:bg-yellow-400"
                  >{specialPriceSelection.size > 0 ? `Done (${specialPriceSelection.size})` : 'Done'}</button>
                </div>
              </div>
              <div className="max-h-48 overflow-y-auto divide-y divide-[var(--border)]">
                {/* Only show base countries that aren't already special */}
                {countriesWithBase.length === 0 && (
                  <p className="p-3 text-sm text-[var(--muted)] text-center">
                    No countries in the base list — add countries first before setting special prices
                  </p>
                )}
                {countriesWithBase.map((c) => {
                  const isSelected = specialPriceSelection.has(c.code);
                  return (
                    <label
                      key={c.code}
                      className={`flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors ${isSelected ? 'bg-yellow-500/10' : 'hover:bg-[var(--card)]'}`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {
                          setSpecialPriceSelection((prev) => {
                            const next = new Set(prev);
                            if (next.has(c.code)) next.delete(c.code);
                            else next.add(c.code);
                            return next;
                          });
                        }}
                        className="w-4 h-4 rounded accent-yellow-500"
                      />
                      <span className="text-lg">{c.flag_emoji}</span>
                      <div className="flex-1">
                        <div className="text-sm text-[var(--foreground)]">{c.name}</div>
                        <div className="text-xs text-[var(--muted)]">{c.code}</div>
                      </div>
                      <span className="text-xs text-[var(--muted)]">base</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Countries using base price */}
          {countriesWithBase.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-[var(--muted)] mb-2 font-medium uppercase tracking-wide">
                Using Base Price — {fmt(parseFloat(basePrice) || 0)}
              </p>
              <div className="flex flex-wrap gap-2">
                {countriesWithBase.map((c) => (
                  <span
                    key={c.code}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-sm bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)]"
                  >
                    {getCountryFlag(c.code)} {c.code}
                    <button
                      onClick={() => handleRemoveCountry(c.code)}
                      className="ml-1 text-[var(--muted)] hover:text-red-400"
                    >✕</button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Countries with special price */}
          {countriesWithOverrides.length > 0 && (
            <div>
              <p className="text-xs text-yellow-400 mb-2 font-medium uppercase tracking-wide">
                Special Prices — Custom rate per country
              </p>
              <div className="space-y-2">
                {countriesWithOverrides.map((c) => {
                  const val = specialCountries.get(c.code);
                  const status = saveStatus.get(c.code);
                  return (
                    <div key={c.code} className="flex flex-col sm:flex-row sm:items-center gap-2 p-2 rounded-lg bg-yellow-500/5 border border-yellow-500/30">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-sm">{getCountryFlag(c.code)} {c.code}</span>
                        <button
                          onClick={() => handleRemoveCountry(c.code)}
                          className="text-[var(--muted)] hover:text-red-400 text-xs"
                        >✕</button>
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 w-full">
                        <input
                          type="number"
                          min={1}
                          step={100}
                          value={val ?? ''}
                          onChange={(e) => setOverride(c.code, e.target.value)}
                          placeholder={basePrice || '0'}
                          className="w-20 px-2 py-1.5 rounded bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] text-xs focus:outline-none focus:ring-1 focus:ring-yellow-500"
                        />
                        <span className="text-[10px] text-[var(--muted)] shrink-0">
                          ₦/{isIP ? 'IP' : 'GB'}
                        </span>
                        {/* Save: update DB with new special price */}
                        <button
                          onClick={async () => {
                            const price = specialCountries.get(c.code);
                            if (price == null || price <= 0) return;
                            setSaveStatus((prev) => new Map(prev).set(c.code, 'saving'));
                            const res = await api.updateCountryPlanType(c.code, product.plan_type, {
                              enabled: true,
                              is_special: true,
                              price_per_ip: isIP ? price : undefined,
                              price_per_gb: !isIP ? price : undefined,
                            });
                            setSaveStatus((prev) => {
                              const next = new Map(prev);
                              next.set(c.code, res.error ? 'idle' : 'saved');
                              setTimeout(() => setSaveStatus((s) => { const n = new Map(s); n.delete(c.code); return n; }), 2000);
                              return next;
                            });
                          }}
                          disabled={status === 'saving' || val == null || val <= 0}
                          className="px-3 py-1 rounded text-xs font-medium shrink-0 bg-yellow-500 text-black hover:bg-yellow-400 disabled:opacity-40"
                        >
                          {status === 'saving' ? '...' : status === 'saved' ? '✓ Saved' : 'Save'}
                        </button>
                        {/* Reset: clear special, move country back to base */}
                        <button
                          onClick={async () => {
                            setSaveStatus((prev) => new Map(prev).set(c.code, 'saving'));
                            await api.removeCountryFromProduct(c.code, product.plan_type);
                            // Local state: move back to base
                            setSpecialCountries((prev) => { const n = new Map(prev); n.delete(c.code); return n; });
                            setBaseCountries((prev) => new Set([...prev, c.code]));
                            setSaveStatus((prev) => { const n = new Map(prev); n.delete(c.code); return n; });
                          }}
                          className="px-2 py-1 rounded text-xs text-[var(--muted)] hover:text-orange-400 shrink-0 border border-[var(--border)]"
                          title="Reset to base price"
                        >Reset</button>
                        {/* Delete: remove country from product entirely */}
                        <button
                          onClick={async () => {
                            await api.removeCountryFromProduct(c.code, product.plan_type);
                            setSpecialCountries((prev) => { const n = new Map(prev); n.delete(c.code); return n; });
                            setBaseCountries((prev) => { const n = new Set(prev); n.delete(c.code); return n; });
                          }}
                          className="px-2 py-1 rounded text-xs text-red-400/60 hover:text-red-400 shrink-0 border border-red-400/30 hover:border-red-400"
                          title="Delete from product"
                        >Delete</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {(baseCountries.size === 0 && specialCountries.size === 0) && (
            <p className="text-sm text-[var(--muted)] text-center py-4">
              No countries selected. Click "Add Countries" to choose which countries this product is available in.
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-4 border-t border-[var(--border)]">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--background)]">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || (baseCountries.size + specialCountries.size === 0)}
            className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function PlanSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('settings');

  const [countries, setCountries] = useState<CountryItem[]>([]);
  const [countriesLoading, setCountriesLoading] = useState(true);
  const [savingCodes, setSavingCodes] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const [productCards, setProductCards] = useState<ProductCard[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [editTarget, setEditTarget] = useState<ProductCard | null>(null);

  const fetchCountries = useCallback(async () => {
    try {
      const res = await api.getAdminCountries();
      if (res.error) { setError('Failed: ' + res.error); return; }
      const data = res.data as any;
      setCountries(data?.countries ?? []);
    } catch { setError('Failed to load countries.'); }
    finally { setCountriesLoading(false); }
  }, []);

  const fetchProductCards = useCallback(async () => {
    setProductsLoading(true);
    try {
      // Fetch countries list AND plans list in parallel
      const [countriesRes, plansRes] = await Promise.all([
        api.getAdminCountries(),
        // Use the admin plans endpoint — add a public method if needed
        api.request('/api/admin/plans'),
      ]);

      if (countriesRes.error) { setError('Failed to load countries: ' + countriesRes.error); return; }
      const allCountries: CountryItem[] = (countriesRes.data as any)?.countries ?? [];
      // plansRes.data is {data: [...], pagination: {...}} — extract the nested array
      const plansData = (plansRes?.data as any)?.data ?? [];

      const cards: ProductCard[] = PRODUCTS.map((p) => {
        // Get codes of countries that actually have a plan row in DB
        const productCountryCodes = new Set(
          plansData
            .filter((plan: any) => plan.plan_type === p.plan_type)
            .map((plan: any) => plan.country)
        );
        // Only include countries that are globally enabled AND have a plan row
        const countryPrefs: CountryPref[] = allCountries
          .filter((c: CountryItem) => c.is_enabled && productCountryCodes.has(c.code))
          .map((c: CountryItem) => ({ code: c.code, is_special: false, override_price: null }));
        return {
          plan_type: p.plan_type,
          label: p.label,
          pricing_model: p.pricing_model,
          base_price: null,
          countries: countryPrefs,
          is_active: countryPrefs.length > 0,
        };
      });

      setProductCards(cards);
    } catch (e) { setError('Failed to load products: ' + String(e)); }
    finally { setProductsLoading(false); }
  }, []);

  useEffect(() => { fetchCountries(); }, [fetchCountries]);

  useEffect(() => {
    if (activeTab === 'settings' && productCards.length === 0 && !productsLoading) {
      fetchProductCards();
    }
  }, [activeTab, productCards.length, productsLoading, fetchProductCards]);

  const handleToggleCountry = async (code: string, currentEnabled: boolean) => {
    setSavingCodes((prev) => new Set(prev).add(code));
    const planTypes = ['DC', 'ISP', 'RESIDENTIAL', 'MOBILE'];
    await api.toggleCountry(code, !currentEnabled);
    setCountries((prev) =>
      prev.map((c) =>
        c.code !== code
          ? c
          : { ...c, is_enabled: !currentEnabled, enabled_plan_types: currentEnabled ? [] : c.enabled_plan_types }
      )
    );
    setSavingCodes((prev) => { const n = new Set(prev); n.delete(code); return n; });
  };

  return (
    <div className="space-y-6 px-4 md:px-0">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Plan Management</h1>
        <p className="text-[var(--muted)] text-sm">
          {activeTab === 'settings'
            ? '4 proxy products — set base price and override prices for specific countries'
            : 'Toggle countries active or inactive globally across all products'}
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

      {/* ── Settings Tab: 4 Product Cards ── */}
      {activeTab === 'settings' && (
        productsLoading ? (
          <div className="flex items-center justify-center min-h-[200px]">
            <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            {productCards.map((card) => (
              <div
                key={card.plan_type}
                className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden"
              >
                {/* Card header */}
                <div className="flex items-center justify-between px-5 py-4 bg-[var(--background)]">
                  <div className="flex items-center gap-3">
                    <span className={`inline-block w-2 h-2 rounded-full ${card.is_active ? 'bg-green-500' : 'bg-gray-500'}`} />
                    <h3 className="text-base font-semibold text-[var(--foreground)]">{card.label}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      card.pricing_model === 'per_IP'
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-purple-500/20 text-purple-400'
                    }`}>
                      {card.pricing_model === 'per_IP' ? 'per IP' : 'per GB'}
                    </span>
                    <span className="text-sm text-[var(--muted)]">
                      {card.countries.length} country{card.countries.length !== 1 ? 'ies' : ''}
                    </span>
                  </div>
                  <button
                    onClick={() => setEditTarget(card)}
                    className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-sm text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors"
                  >
                    Edit
                  </button>
                </div>

                {/* Country chips */}
                {card.countries.length > 0 && (
                  <div className="px-5 py-3 flex flex-wrap gap-2">
                    {card.countries.map((c) => {
                      const hasOverride = c.override_price != null;
                      return (
                        <span
                          key={c.code}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-sm border ${
                            hasOverride
                              ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
                              : 'bg-[var(--background)] border-[var(--border)] text-[var(--foreground)]'
                          }`}
                        >
                          <span>{getCountryFlag(c.code)}</span>
                          <span>{c.code}</span>
                          {hasOverride && (
                            <span className="text-xs ml-1 opacity-75">
                              → {fmt(c.override_price!)}
                            </span>
                          )}
                        </span>
                      );
                    })}
                  </div>
                )}

                {card.countries.length === 0 && (
                  <div className="px-5 py-3 text-sm text-[var(--muted)]">
                    Not available anywhere yet — click Edit to add countries
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {/* ── Countries Tab ── */}
      {activeTab === 'countries' && (
        countriesLoading ? (
          <div className="flex items-center justify-center min-h-[300px]">
            <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[400px]">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Country</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">Active</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Enabled In</th>
                  </tr>
                </thead>
                <tbody>
                  {[...countries].sort((a, b) => getCountryName(a.code).localeCompare(getCountryName(b.code))).map((country) => {
                    const isActive = country.is_enabled;
                    const saving = savingCodes.has(country.code);
                    return (
                      <tr key={country.code} className="border-b border-[var(--border)] hover:bg-[var(--background)]/50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{country.flag_emoji}</span>
                            <div>
                              <div className="font-medium text-[var(--foreground)]">{country.name}</div>
                              <div className="text-xs text-[var(--muted)]">{country.code}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => !saving && handleToggleCountry(country.code, isActive)}
                            disabled={saving}
                            className={`relative w-10 h-5 rounded-full transition-colors disabled:opacity-40 ${
                              isActive ? 'bg-green-500' : 'bg-gray-600'
                            }`}
                          >
                            <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                              isActive ? 'translate-x-5' : 'translate-x-0'
                            }`} />
                          </button>
                        </td>
                        <td className="px-4 py-3">
                          {isActive ? (
                            <div className="flex flex-wrap gap-1">
                              {country.enabled_plan_types.map((pt) => (
                                <span key={pt} className="text-xs px-1.5 py-0.5 rounded bg-[var(--primary)]/10 text-[var(--primary)]">
                                  {pt}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-sm text-[var(--muted)]">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-[var(--border)] text-sm text-[var(--muted)]">
              {countries.filter((c) => c.enabled_plan_types.length > 0).length} of {countries.length} countries active
            </div>
          </div>
        )
      )}

      {/* Edit Modal */}
      {editTarget && (
        <EditProductModal
          product={editTarget}
          allCountries={countries}
          onSaved={() => { fetchProductCards(); fetchCountries(); }}
          onClose={() => setEditTarget(null)}
        />
      )}
    </div>
  );
}
