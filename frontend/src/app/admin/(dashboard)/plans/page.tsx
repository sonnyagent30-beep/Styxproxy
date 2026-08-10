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
  override_price: number | null; // null = use base price
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
  const [countryPrefs, setCountryPrefs] = useState<Map<string, number | null>>(
    new Map(product.countries.map((c) => [c.code, c.override_price]))
  );
  const [isActive, setIsActive] = useState(product.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCountryPicker, setShowCountryPicker] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');

  // Only show globally active countries in the picker ( Countries tab gate )
  const filtered = allCountries.filter((c) =>
    getCountryName(c.code).toLowerCase().includes(countrySearch.toLowerCase()) ||
    c.code.toLowerCase().includes(countrySearch.toLowerCase())
  );

  const toggleCountry = (code: string) => {
    setCountryPrefs((prev) => {
      const next = new Map(prev);
      if (next.has(code)) next.delete(code);
      else next.set(code, null); // null = use base price
      return next;
    });
  };

  const setOverride = (code: string, value: string) => {
    setCountryPrefs((prev) => {
      const next = new Map(prev);
      next.set(code, value === '' ? null : parseFloat(value));
      return next;
    });
  };

  const handleRemoveCountry = async (code: string) => {
    await api.removeCountryFromProduct(code, product.plan_type);
    setCountryPrefs((prev) => {
      const next = new Map(prev);
      next.delete(code);
      return next;
    });
  };

  const handleSave = async () => {
    if (!basePrice || parseFloat(basePrice) <= 0) { setError('Enter a base price'); return; }
    setSaving(true);
    setError(null);

    const selectedCodes = [...countryPrefs.keys()];
    const res = await api.createProductsBulk({
      plan_type: product.plan_type,
      pricing_model: product.pricing_model,
      price: parseFloat(basePrice),
      countries: selectedCodes,
      is_active: isActive,
    });

    if (res.error) { setError('Failed: ' + res.error); setSaving(false); return; }

    // Update override prices for each selected country
    await Promise.all(
      selectedCodes.map((code) => {
        const override = countryPrefs.get(code);
        return api.updateCountryPlanType(code, product.plan_type, {
          enabled: true,
          price_per_ip: isIP ? (override ?? parseFloat(basePrice)) : undefined,
          price_per_gb: !isIP ? (override ?? parseFloat(basePrice)) : undefined,
        });
      })
    );

    onSaved();
    onClose();
    setSaving(false);
  };

  const selectedCountries = allCountries.filter((c) => countryPrefs.has(c.code));
  const countriesWithOverrides = selectedCountries.filter((c) => countryPrefs.get(c.code) != null);
  const countriesWithBase = selectedCountries.filter((c) => countryPrefs.get(c.code) == null);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto py-8">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-2xl p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl my-4">
        <h2 className="text-lg font-bold text-[var(--foreground)] mb-1">Edit: {product.label}</h2>
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
              Countries ({countryPrefs.size} selected)
            </label>
            <button
              type="button"
              onClick={() => setShowCountryPicker((v) => !v)}
              className="text-sm text-[var(--primary)] hover:underline"
            >
              {showCountryPicker ? 'Done' : 'Add Countries'}
            </button>
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
                  const selected = countryPrefs.has(c.code);
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
              <p className="text-xs text-[var(--muted)] mb-2 font-medium uppercase tracking-wide">
                Special Prices
              </p>
              <div className="space-y-2">
                {countriesWithOverrides.map((c) => {
                  const val = countryPrefs.get(c.code);
                  return (
                    <div key={c.code} className="flex items-center gap-3">
                      <span className="flex items-center gap-1.5 text-sm text-[var(--foreground)] w-40 shrink-0">
                        {getCountryFlag(c.code)} {c.code}
                      </span>
                      <input
                        type="number"
                        min={1}
                        step={100}
                        value={val ?? ''}
                        onChange={(e) => setOverride(c.code, e.target.value)}
                        placeholder={basePrice}
                        className="flex-1 px-2 py-1 rounded bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                      />
                      <span className="text-xs text-[var(--muted)] shrink-0">
                        ₦/{isIP ? 'IP' : 'GB'}
                        {basePrice && val != null && parseFloat(String(val)) !== parseFloat(basePrice) && (
                          <span className="ml-1 text-green-400">
                            ({parseFloat(String(val)) > parseFloat(basePrice) ? '+' : ''}
                            {fmt(parseFloat(String(val)) - parseFloat(basePrice))})
                          </span>
                        )}
                      </span>
                      <button
                        onClick={() => setOverride(c.code, '')}
                        className="text-xs text-[var(--muted)] hover:text-red-400 shrink-0"
                        title="Use base price"
                      >Reset</button>
                      <button
                        onClick={() => handleRemoveCountry(c.code)}
                        className="text-[var(--muted)] hover:text-red-400 shrink-0"
                      >✕</button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {countryPrefs.size === 0 && (
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
            disabled={saving || countryPrefs.size === 0}
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
      const res = await api.getAdminCountries();
      if (res.error) { setError('Failed: ' + res.error); return; }
      const data = res.data as any;
      const allCountries: CountryItem[] = data?.countries ?? [];

      // Also fetch CPT details to get per-country prices
      const cards: ProductCard[] = await Promise.all(
        PRODUCTS.map(async (p) => {
          const enabledCountries = allCountries.filter((c: CountryItem) => c.enabled_plan_types.map(t => t.toUpperCase()).includes(p.plan_type));
          // Get per-country override prices
          const countryPrefs: CountryPref[] = await Promise.all(
            enabledCountries.map(async (c: CountryItem) => {
              try {
                const detail = await api.getAdminCountry(c.code) as any;
                const ptData = detail.data?.plan_types?.[p.plan_type];
                return {
                  code: c.code,
                  override_price: ptData?.price_per_ip ?? ptData?.price_per_gb ?? null,
                };
              } catch {
                return { code: c.code, override_price: null };
              }
            })
          );
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
    await Promise.all(
      planTypes.map((pt) => api.updateCountryPlanType(code, pt, { enabled: !currentEnabled }))
    );
    setCountries((prev) =>
      prev.map((c) =>
        c.code !== code
          ? c
          : { ...c, enabled_plan_types: currentEnabled ? [] : planTypes }
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
                    const isActive = country.enabled_plan_types.length > 0;
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
