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
  const [countryPrices, setCountryPrices] = useState<Map<string, number>>(new Map());
  const [basePrice, setBasePrice] = useState(String(product.base_price ?? ''));
  const [isActive, setIsActive] = useState(product.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const [pickerLoading, setPickerLoading] = useState(false);

  // Load prices from DB when modal opens
  useEffect(() => {
    const load = async () => {
      setPickerLoading(true);
      const prices = new Map<string, number>();
      for (const c of allCountries) {
        try {
          const res = await api.getAdminCountry(c.code);
          if (res.error) continue;
          const data = res.data as any;
          const pt = data?.plan_types?.[product.plan_type];
          if (!pt || pt.price_per_ip === null && pt.price_per_gb === null) continue;
          const price = isIP ? (pt.price_per_ip ?? 0) : (pt.price_per_gb ?? 0);
          prices.set(c.code, price);
        } catch {}
      }
      setCountryPrices(prices);
      if (prices.size > 0) {
        const first = prices.values().next().value;
        if (first) setBasePrice(String(first));
      }
      setPickerLoading(false);
    };
    load();
  }, []);

  // Countries in this product (have a price set)
  const productCountries = allCountries.filter((c) => countryPrices.has(c.code));

  // Picker: show all countries not yet in product
  const pickerCountries = allCountries.filter(
    (c) => !countryPrices.has(c.code) && (
      getCountryName(c.code).toLowerCase().includes(countrySearch.toLowerCase()) ||
      c.code.toLowerCase().includes(countrySearch.toLowerCase())
    )
  );

  const addCountry = async (code: string) => {
    if (!basePrice || parseFloat(basePrice) <= 0) return;
    setSaving(true);
    await api.createProductsBulk({
      plan_type: product.plan_type,
      pricing_model: product.pricing_model,
      price: parseFloat(basePrice),
      countries: [code],
      is_active: true,
    });
    setCountryPrices((prev) => new Map(prev).set(code, parseFloat(basePrice)));
    setSaving(false);
  };

  const removeCountry = async (code: string) => {
    await api.removeCountryFromProduct(code, product.plan_type);
    setCountryPrices((prev) => { const n = new Map(prev); n.delete(code); return n; });
  };

  const updatePrice = async (code: string, value: string) => {
    const num = value === '' ? null : parseFloat(value);
    const newPrices = new Map(countryPrices);
    if (num == null) {
      newPrices.delete(code);
    } else {
      newPrices.set(code, num);
    }
    setCountryPrices(newPrices);
    if (num != null) {
      await api.updateCountryPlanType(code, product.plan_type, {
        enabled: true,
        price_per_ip: isIP ? num : undefined,
        price_per_gb: !isIP ? num : undefined,
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto py-8 px-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl my-4">

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-[var(--border)]">
          <div>
            <h2 className="text-base font-bold text-[var(--foreground)]">{product.label}</h2>
            <p className="text-xs text-[var(--muted)] mt-0.5">
              {productCountries.length} countr{productCountries.length !== 1 ? 'ies' : 'y'} · {isIP ? 'per IP/month' : 'per GB'}
            </p>
          </div>
          <button onClick={onClose} className="text-[var(--muted)] hover:text-[var(--foreground)] p-1">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-xs">{error}</div>
          )}

          {/* Base Price */}
          <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--background)]">
            <label className="block text-xs font-medium text-[var(--muted)] mb-1.5">
              Base Price — template for new countries
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-[var(--muted)]">₦</span>
              <input
                type="number"
                min={1}
                step={100}
                value={basePrice}
                onChange={(e) => setBasePrice(e.target.value)}
                placeholder="Enter base price"
                className="flex-1 px-2 py-1.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
              />
              <span className="text-xs text-[var(--muted)]">/{isIP ? 'IP' : 'GB'}/mo</span>
            </div>
          </div>

          {/* Countries Header */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[var(--muted)]">
                Countries{productCountries.length > 0 ? ` (${productCountries.length})` : ''}
              </span>
              <button
                onClick={() => setShowPicker((v) => !v)}
                className="text-xs text-[var(--primary)] hover:underline"
              >
                {showPicker ? 'Done' : '+ Add Country'}
              </button>
            </div>

            {/* Country Picker */}
            {showPicker && (
              <div className="mb-3 border border-[var(--border)] rounded-lg bg-[var(--background)] overflow-hidden">
                <div className="p-2 border-b border-[var(--border)]">
                  <input
                    type="text"
                    value={countrySearch}
                    onChange={(e) => setCountrySearch(e.target.value)}
                    placeholder="Search..."
                    className="w-full px-2 py-1 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] text-xs focus:outline-none"
                    autoFocus
                  />
                </div>
                <div className="max-h-40 overflow-y-auto">
                  {pickerLoading ? (
                    <p className="p-3 text-xs text-[var(--muted)] text-center">Loading...</p>
                  ) : pickerCountries.length === 0 ? (
                    <p className="p-3 text-xs text-[var(--muted)] text-center">No countries found</p>
                  ) : (
                    pickerCountries.map((c) => (
                      <label
                        key={c.code}
                        className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-[var(--card)]"
                      >
                        <button
                          onClick={() => addCountry(c.code)}
                          disabled={!basePrice || parseFloat(basePrice) <= 0 || saving}
                          className="text-xs text-[var(--primary)] hover:underline disabled:opacity-50"
                        >
                          + Add
                        </button>
                        <span className="text-base">{c.flag_emoji}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-[var(--foreground)] truncate">{c.name}</div>
                        </div>
                        <div className="text-xs text-[var(--muted)]">{c.code}</div>
                      </label>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Country Price Rows */}
            {productCountries.length === 0 ? (
              <div className="text-center py-6 text-xs text-[var(--muted)] border border-dashed border-[var(--border)] rounded-lg">
                No countries yet. Click "+ Add Country" above.
              </div>
            ) : (
              <div className="space-y-1.5">
                {productCountries.map((c) => {
                  const price = countryPrices.get(c.code) ?? null;
                  return (
                    <div key={c.code} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)]">
                      <span className="text-base shrink-0">{c.flag_emoji}</span>
                      <span className="text-[var(--foreground)] font-medium w-6 shrink-0">{c.code}</span>
                      <input
                        type="number"
                        min={1}
                        step={100}
                        value={price ?? ''}
                        onChange={(e) => updatePrice(c.code, e.target.value)}
                        onBlur={(e) => updatePrice(c.code, e.target.value)}
                        placeholder={basePrice || '—'}
                        className="flex-1 px-2 py-1 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] text-xs focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                      />
                      <span className="text-[10px] text-[var(--muted)] shrink-0">
                        ₦/{isIP ? 'IP' : 'GB'}
                      </span>
                      <button
                        onClick={() => removeCountry(c.code)}
                        className="text-[var(--muted)] hover:text-red-400 shrink-0"
                        title="Remove"
                      >✕</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Active Toggle */}
          <div className="flex items-center gap-3">
            <div
              onClick={() => setIsActive(!isActive)}
              className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer ${isActive ? 'bg-green-500' : 'bg-gray-600'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${isActive ? 'translate-x-4' : 'translate-x-0'}`} />
            </div>
            <span className="text-xs text-[var(--foreground)]">{isActive ? 'Active' : 'Inactive'}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 pb-5 flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            Close
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
      const res = await api.getAdminCountries();
      if (res.error) { setError('Failed: ' + res.error); return; }
      const data = res.data as any;
      const allCountries: CountryItem[] = data?.countries ?? [];

      // Also fetch CPT details to get per-country prices
      const cards: ProductCard[] = await Promise.all(
        PRODUCTS.map(async (p) => {
          const enabledCountries = allCountries.filter((c: CountryItem) => c.enabled_plan_types.map(t => t.toUpperCase()).includes(p.plan_type));
          // Get per-country override prices
          // Note: is_special and actual prices are loaded per-country in the modal
          // Here we just show which countries are in the product
          const countryPrefs: CountryPref[] = enabledCountries.map((c: CountryItem) => ({
            code: c.code,
            is_special: false,
            override_price: null,
          }));
          return {
            plan_type: p.plan_type,
            label: p.label,
            pricing_model: p.pricing_model,
            base_price: null,
            countries: countryPrefs,
            is_active: countryPrefs.length > 0,
          };
        })
      );

      setProductCards(cards);
    } catch { setError('Failed to load products.'); }
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
