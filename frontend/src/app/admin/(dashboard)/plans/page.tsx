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
  const [countrySearch, setCountrySearch] = useState('');  // Fetch is_special + price for ALL enabled countries when modal opens
  // We don't know which countries are in the product, so we check all globally-enabled ones
  const loadPrices = useCallback(async () => {
    // Get all globally-enabled country codes for this plan_type
    const enabledCodes = allCountries
      .filter((c) => c.enabled_plan_types.map((t) => t.toUpperCase()).includes(product.plan_type))
      .map((c) => c.code);

    if (enabledCodes.length === 0) return;

    const newSpecial = new Map<string, number | null>();
    const newBase = new Set<string>();

    await Promise.all(
      enabledCodes.map(async (code) => {
        try {
          const res = await api.getAdminCountry(code);
          if (res.error) return;
          const data = res.data as any;
          const ptData = data?.plan_types?.[product.plan_type];
          if (ptData?.is_special) {
            // Country is special — use its stored price
            const price = isIP ? ptData.price_per_ip : ptData.price_per_gb;
            newSpecial.set(code, price ?? null);
          } else {
            // Country is in the product at base price
            newBase.add(code);
          }
        } catch {}
      })
    );

    setSpecialCountries(newSpecial);
    setBaseCountries(newBase);

    // Load base price from any base country
    if (newBase.size > 0 && !basePrice) {
      const firstBase = [...newBase][0];
      try {
        const res = await api.getAdminCountry(firstBase);
        if (!res.error) {
          const data = res.data as any;
          const ptData = data?.plan_types?.[product.plan_type];
          if (ptData && !ptData.is_special) {
            const bp = isIP ? ptData.price_per_ip : ptData.price_per_gb;
            if (bp) setBasePrice(String(bp));
          }
        }
      } catch {}
    }
  }, [product.plan_type, isIP]);

  useEffect(() => { loadPrices(); }, [loadPrices]);

  // Only show globally active countries in the picker ( Countries tab gate )
  const pickerCountries = allCountries.filter((c) => c.is_enabled);
  const filtered = pickerCountries.filter((c) =>
    getCountryName(c.code).toLowerCase().includes(countrySearch.toLowerCase()) ||
    c.code.toLowerCase().includes(countrySearch.toLowerCase())
  );

  const toggleCountry = async (code: string) => {
    const isAdding = !baseCountries.has(code) && !specialCountries.has(code);
    if (isAdding) {
      // Add: save to DB at base price, show in base section
      if (basePrice && parseFloat(basePrice) > 0) {
        await api.createProductsBulk({
          plan_type: product.plan_type,
          pricing_model: product.pricing_model,
          price: parseFloat(basePrice),
          countries: [code],
          is_active: true,
        });
      }
      setBaseCountries((prev) => new Set([...prev, code]));
      setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
    } else {
      // Remove: delete from DB, remove from state
      await api.removeCountryFromProduct(code, product.plan_type);
      setBaseCountries((prev) => { const n = new Set(prev); n.delete(code); return n; });
      setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
    }
  };

  const setOverride = async (code: string, value: string) => {
    const num = value === '' ? null : parseFloat(value);
    if (num == null) {
      // Reset: move back to base — remove from special, add to base, save
      setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
      setBaseCountries((prev) => new Set([...prev, code]));
      // Save as base price via bulk create
      if (basePrice && parseFloat(basePrice) > 0) {
        await api.createProductsBulk({
          plan_type: product.plan_type,
          pricing_model: product.pricing_model,
          price: parseFloat(basePrice),
          countries: [code],
          is_active: true,
        });
      }
    } else {
      // Set special price
      setSpecialCountries((prev) => new Map(prev).set(code, num));
      setBaseCountries((prev) => { const n = new Set(prev); n.delete(code); return n; });
      // Save immediately
      setSaveStatus((prev) => new Map(prev).set(code, 'saving'));
      const res = await api.updateCountryPlanType(code, product.plan_type, {
        enabled: true,
        is_special: true,
        price_per_ip: isIP ? num : undefined,
        price_per_gb: !isIP ? num : undefined,
      });
      setSaveStatus((prev) => {
        const next = new Map(prev);
        next.set(code, res.error ? 'idle' : 'saved');
        setTimeout(() => setSaveStatus((s) => { const n = new Map(s); n.delete(code); return n; }), 2000);
        return next;
      });
    }
  };

  const handleRemoveCountry = async (code: string) => {
    await api.removeCountryFromProduct(code, product.plan_type);
    setBaseCountries((prev) => { const n = new Set(prev); n.delete(code); return n; });
    setSpecialCountries((prev) => { const n = new Map(prev); n.delete(code); return n; });
  };

  const handleSave = () => {
    // All saves are per-item now; this just closes the modal
    onSaved();
    onClose();
  };



  // All countries in this product (base + special combined)
  const allProductCountries = allCountries.filter(
    (c) => baseCountries.has(c.code) || specialCountries.has(c.code)
  );
  const specialCount = specialCountries.size;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto py-8 px-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl my-4">

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-[var(--border)]">
          <div>
            <h2 className="text-base font-bold text-[var(--foreground)]">{product.label}</h2>
            <p className="text-xs text-[var(--muted)] mt-0.5">
              {allProductCountries.length} country{allProductCountries.length !== 1 ? 'ies' : 'y'} · {isIP ? 'per IP/month' : 'per GB'}
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

          {/* Base Price — the template */}
          <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--background)]">
            <label className="block text-xs font-medium text-[var(--muted)] mb-1.5">
              Base Price — applies to all countries
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

          {/* Countries Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[var(--muted)]">
                Countries {allProductCountries.length > 0 && `(${allProductCountries.length})`}
              </span>
              <div className="flex gap-3">
                {product.plan_type === 'DC' || product.plan_type === 'ISP' ? (
                  <button
                    onClick={() => { setShowCountryPicker((v) => !v); setShowSpecialPricePicker(false); }}
                    className="text-xs text-[var(--primary)] hover:underline"
                  >
                    {showCountryPicker ? 'Done' : '+ Add Country'}
                  </button>
                ) : (
                  <button
                    onClick={() => { setShowCountryPicker((v) => !v); setShowSpecialPricePicker(false); }}
                    className="text-xs text-[var(--primary)] hover:underline"
                  >
                    {showCountryPicker ? 'Done' : '+ Add Country'}
                  </button>
                )}
              </div>
            </div>

            {/* Country Picker */}
            {showCountryPicker && (
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
                  {filtered.length === 0 ? (
                    <p className="p-3 text-xs text-[var(--muted)] text-center">
                      No countries found
                    </p>
                  ) : (
                    filtered.map((c) => {
                      const inProduct = baseCountries.has(c.code) || specialCountries.has(c.code);
                      return (
                        <label
                          key={c.code}
                          className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-[var(--card)]"
                        >
                          <input
                            type="checkbox"
                            checked={inProduct}
                            onChange={() => toggleCountry(c.code)}
                            className="w-3.5 h-3.5 rounded accent-[var(--primary)]"
                          />
                          <span className="text-base">{c.flag_emoji}</span>
                          <div className="flex-1 min-w-0">
                            <div className="text-xs text-[var(--foreground)] truncate">{c.name}</div>
                          </div>
                          <div className="text-xs text-[var(--muted)]">{c.code}</div>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Country Price Rows */}
            {allProductCountries.length === 0 ? (
              <div className="text-center py-6 text-xs text-[var(--muted)] border border-dashed border-[var(--border)] rounded-lg">
                No countries yet. Click "+ Add Country" above.
              </div>
            ) : (
              <div className="space-y-1.5">
                {allProductCountries.map((c) => {
                  const isSpecial = specialCountries.has(c.code);
                  const price = specialCountries.get(c.code) ?? (basePrice ? parseFloat(basePrice) : null);
                  const status = saveStatus.get(c.code);
                  const diff = price != null && basePrice && parseFloat(basePrice) !== price
                    ? price - parseFloat(basePrice)
                    : null;
                  return (
                    <div key={c.code} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs ${isSpecial ? 'bg-amber-500/5 border-amber-500/30' : 'bg-[var(--background)] border-[var(--border)]'}`}>
                      {/* Country */}
                      <span className="text-base shrink-0">{c.flag_emoji}</span>
                      <span className="text-[var(--foreground)] font-medium w-6 shrink-0">{c.code}</span>
                      {/* Price Input */}
                      <div className="flex-1 min-w-0">
                        <input
                          type="number"
                          min={1}
                          step={100}
                          value={price ?? ''}
                          onChange={(e) => {
                            const v = e.target.value;
                            const num = v === '' ? null : parseFloat(v);
                            if (num != null) {
                              setSpecialCountries((prev) => new Map(prev).set(c.code, num));
                              setBaseCountries((prev) => { const n = new Set(prev); n.delete(c.code); return n; });
                            }
                          }}
                          onBlur={() => {
                            const p = price ?? (basePrice ? parseFloat(basePrice) : null);
                            if (p == null) return;
                            setSaveStatus((prev) => new Map(prev).set(c.code, 'saving'));
                            const isSpec = !baseCountries.has(c.code) && specialCountries.has(c.code);
                            api.updateCountryPlanType(c.code, product.plan_type, {
                              enabled: true,
                              is_special: isSpec,
                              price_per_ip: isIP ? p : undefined,
                              price_per_gb: !isIP ? p : undefined,
                            }).then((res) => {
                              setSaveStatus((prev) => {
                                const next = new Map(prev);
                                next.set(c.code, res.error ? 'idle' : 'saved');
                                setTimeout(() => setSaveStatus((s) => { const n = new Map(s); n.delete(c.code); return n; }), 2000);
                                return next;
                              });
                            });
                          }}
                          placeholder={basePrice || '—'}
                          className={`w-full px-2 py-1 rounded text-xs focus:outline-none focus:ring-1 ${isSpecial ? 'bg-[var(--background)] border border-amber-500/50 text-[var(--foreground)] focus:ring-amber-500' : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:ring-[var(--primary)]'}`}
                        />
                      </div>
                      {/* Diff indicator */}
                      <span className="text-[10px] shrink-0 w-12 text-right">
                        {diff != null ? (
                          <span className={diff > 0 ? 'text-green-400' : 'text-red-400'}>
                            {diff > 0 ? '+' : ''}{fmt(diff)}
                          </span>
                        ) : baseCountries.has(c.code) ? (
                          <span className="text-[var(--muted)]">base</span>
                        ) : null}
                      </span>
                      {/* Status */}
                      <span className="w-5 shrink-0 text-center">
                        {status === 'saving' && <span className="text-yellow-400">·</span>}
                        {status === 'saved' && <span className="text-green-400">✓</span>}
                      </span>
                      {/* Remove */}
                      <button
                        onClick={() => handleRemoveCountry(c.code)}
                        className="text-[var(--muted)] hover:text-red-400 shrink-0"
                        title="Remove"
                      >✕</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Active toggle */}
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
          <button
            onClick={handleSave}
            disabled={saving || allProductCountries.length === 0}
            className="px-4 py-2 rounded-lg text-xs bg-[var(--primary)] text-white font-medium hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
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
