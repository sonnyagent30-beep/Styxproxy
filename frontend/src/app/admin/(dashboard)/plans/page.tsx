'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { COUNTRIES } from '@/lib/products';

// ─── Types ────────────────────────────────────────────────────────────────────
type Tab = 'settings' | 'countries';

// Country row from API
interface CountryItem {
  code: string;
  name: string;
  flag_emoji: string;
  region: string;
  enabled_plan_types: string[];
}

// Product (from plans table)
interface Product {
  id: number;
  plan_code: string;
  plan_type: string;
  country: string;
  price_ngn: number;
  price_per_gb: number | null;
  price_per_ip: number | null;
  quantity: number;
  is_active: boolean;
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
  { value: 'DC', label: 'Datacenter', pricing_model: 'per_IP' },
  { value: 'ISP', label: 'ISP Proxies', pricing_model: 'per_IP' },
  { value: 'RESIDENTIAL', label: 'Residential', pricing_model: 'per_GB' },
  { value: 'MOBILE', label: 'Mobile 4G', pricing_model: 'per_GB' },
] as const;

const PLAN_TYPE_LABELS: Record<string, string> = {
  DC: 'Datacenter',
  ISP: 'ISP Proxies',
  RESIDENTIAL: 'Residential',
  MOBILE: 'Mobile',
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

// ─── Product Builder Modal ─────────────────────────────────────────────────────
interface ProductModalProps {
  editProduct?: Product;
  onSaved: () => void;
  onClose: () => void;
}

function ProductModal({ editProduct, onSaved, onClose }: ProductModalProps) {
  const isEdit = !!editProduct;
  const [form, setForm] = useState<ProductForm>({
    plan_type: editProduct?.plan_type ?? 'DC',
    pricing_model: editProduct?.plan_type === 'RESIDENTIAL' || editProduct?.plan_type === 'MOBILE' ? 'per_GB' : 'per_IP',
    price: editProduct
      ? String(editProduct.price_per_ip ?? editProduct.price_per_gb ?? editProduct.price_ngn)
      : '',
    countries: editProduct ? [editProduct.country] : [],
    is_active: editProduct?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCountryPicker, setShowCountryPicker] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');

  const isIP = form.pricing_model === 'per_GB' ? false : true;

  const ALL_COUNTRY_CODES = Object.keys(COUNTRIES).sort((a, b) =>
    getCountryName(a).localeCompare(getCountryName(b))
  );

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

    let res;
    if (isEdit && editProduct) {
      // Edit existing product
      res = await (api as any).updatePlan(editProduct.id, {
        price_per_ip: isIP ? parseFloat(form.price) : undefined,
        price_per_gb: !isIP ? parseFloat(form.price) : undefined,
        is_active: form.is_active,
      });
    } else {
      // Create new products via bulk builder
      res = await api.createProductsBulk({
        plan_type: form.plan_type,
        pricing_model: isIP ? 'per_IP' : 'per_GB',
        price: parseFloat(form.price),
        countries: form.countries,
        is_active: form.is_active,
      });
    }

    if (res.error) {
      setError('Failed: ' + res.error);
    } else {
      onSaved();
      onClose();
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-[var(--foreground)] mb-1">
          {isEdit ? `Edit: ${editProduct!.plan_code}` : 'Create Product'}
        </h2>
        <p className="text-sm text-[var(--muted)] mb-5">
          {isEdit ? 'Update product type, price and countries' : 'Set up a new proxy product'}
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm">{error}</div>
        )}

        {/* Plan type */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-[var(--muted)] mb-2">Proxy Type</label>
          <div className="grid grid-cols-2 gap-2">
            {PLAN_TYPES.map((pt) => (
              <button
                key={pt.value}
                onClick={() => setForm((f) => ({
                  ...f,
                  plan_type: pt.value,
                  pricing_model: pt.pricing_model,
                  countries: [],
                }))}
                className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
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

        {/* Price */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-[var(--muted)] mb-2">
            Price (₦ {isIP ? 'per IP/month' : 'per GB'})
          </label>
          <input
            type="number" min={1} step={100}
            value={form.price}
            onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
          />
        </div>

        {/* Countries */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-[var(--muted)]">
              Countries ({form.countries.length})
            </label>
            <button
              type="button"
              onClick={() => setShowCountryPicker((v) => !v)}
              className="text-sm text-[var(--primary)] hover:underline"
            >
              {showCountryPicker ? 'Done' : 'Select'}
            </button>
          </div>

          {form.countries.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {form.countries.map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-[var(--primary)]/20 text-[var(--primary)] border border-[var(--primary)]/30"
                >
                  {getCountryFlag(code)} {code}
                  <button onClick={() => toggleCountry(code)} className="hover:text-white">✕</button>
                </span>
              ))}
            </div>
          )}

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
              <div className="max-h-48 overflow-y-auto divide-y divide-[var(--border)]">
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
                      <div>
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

        {/* Active toggle */}
        <div className="mb-5 flex items-center gap-3">
          <div
            onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
            className={`relative w-11 h-6 rounded-full transition-colors cursor-pointer ${form.is_active ? 'bg-green-500' : 'bg-gray-600'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${form.is_active ? 'translate-x-5' : 'translate-x-0'}`} />
          </div>
          <span className="text-sm text-[var(--foreground)]">{form.is_active ? 'Active' : 'Inactive'}</span>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--background)]">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={saving || form.countries.length === 0 || !form.price}
            className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Creating…' : isEdit ? 'Update' : 'Create Product'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function PlanSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('settings');

  // ── Countries tab state ─────────────────────────────
  const [countries, setCountries] = useState<CountryItem[]>([]);
  const [countriesLoading, setCountriesLoading] = useState(true);
  const [savingCodes, setSavingCodes] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // ── Plan Settings tab state ─────────────────────────
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editProduct, setEditProduct] = useState<Product | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Product | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Fetch countries
  const fetchCountries = useCallback(async () => {
    try {
      const res = await api.getAdminCountries();
      if (res.error) { setError('Failed: ' + res.error); return; }
      const data = res.data as any;
      setCountries(data?.countries ?? []);
    } catch { setError('Failed to load countries.'); }
    finally { setCountriesLoading(false); }
  }, []);

  // Fetch products
  const fetchProducts = useCallback(async () => {
    setProductsLoading(true);
    try {
      // Fetch all products (paginated)
      let all: Product[] = [];
      for (let page = 1; page <= 10; page++) {
        const res = await (api as any).getPlans(page, 100);
        if (res.error || !res.data?.data?.length) break;
        all = all.concat(res.data.data);
        if (!res.data.pagination?.has_next) break;
      }
      setProducts(all);
    } catch { setError('Failed to load products.'); }
    finally { setProductsLoading(false); }
  }, []);

  useEffect(() => { fetchCountries(); }, [fetchCountries]);

  useEffect(() => {
    if (activeTab === 'settings' && products.length === 0 && !productsLoading) {
      fetchProducts();
    }
  }, [activeTab, products.length, productsLoading, fetchProducts]);

  // Toggle country active/inactive (enables/disables ALL plan types at once)
  const handleToggleCountry = async (code: string, currentEnabled: boolean) => {
    setSavingCodes((prev) => new Set(prev).add(code));
    // Enable/disable all 4 plan types for this country at once
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

  // Delete product
  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    const res = await (api as any).deletePlan(deleteConfirm.id);
    if (res.error) {
      setError('Delete failed: ' + res.error);
    } else {
      setProducts((prev) => prev.filter((p) => p.id !== deleteConfirm.id));
      setDeleteConfirm(null);
    }
    setDeleting(false);
  };

  const sortedProducts = [...products].sort((a, b) => {
    const typeDiff = a.plan_type.localeCompare(b.plan_type);
    if (typeDiff !== 0) return typeDiff;
    return a.country.localeCompare(b.country);
  });

  return (
    <div className="space-y-6 px-4 md:px-0">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Plan Management</h1>
        <p className="text-[var(--muted)] text-sm">
          {activeTab === 'settings'
            ? 'Create and manage proxy products — type, price, and country coverage'
            : 'Toggle countries active or inactive globally'}
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

      {/* ── Settings Tab: Products ── */}
      {activeTab === 'settings' && (
        <div className="space-y-4">
          {/* Create button */}
          <div className="flex justify-end">
            <button
              onClick={() => { setEditProduct(null); setShowModal(true); }}
              className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white text-sm hover:opacity-90"
            >
              + Create Product
            </button>
          </div>

          {productsLoading ? (
            <div className="flex items-center justify-center min-h-[200px]">
              <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : sortedProducts.length === 0 ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-12 text-center">
              <p className="text-[var(--muted)]">No products yet. Create your first product above.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[600px]">
                  <thead>
                    <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                      <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Product</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Type</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Country</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-[var(--muted)]">Price</th>
                      <th className="px-4 py-3 text-center text-sm font-medium text-[var(--muted)]">Status</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-[var(--muted)]">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedProducts.map((product) => (
                      <tr key={product.id} className="border-b border-[var(--border)] hover:bg-[var(--background)]/50">
                        <td className="px-4 py-3 text-sm text-[var(--foreground)] font-mono">{product.plan_code}</td>
                        <td className="px-4 py-3 text-sm text-[var(--foreground)]">
                          {PLAN_TYPE_LABELS[product.plan_type] ?? product.plan_type}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm">
                            {getCountryFlag(product.country)} {product.country}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-[var(--foreground)]">
                          {fmt(product.price_per_ip ?? product.price_per_gb ?? product.price_ngn)}
                          {(product.price_per_gb != null) && <span className="text-[var(--muted)]">/GB</span>}
                          {(product.price_per_ip != null) && <span className="text-[var(--muted)]">/IP</span>}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            product.is_active
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-gray-600/20 text-gray-400'
                          }`}>
                            {product.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex gap-1 justify-end">
                            <button
                              onClick={() => { setEditProduct(product); setShowModal(true); }}
                              className="px-3 py-1 text-xs rounded border border-[var(--border)] text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(product)}
                              className="px-3 py-1 text-xs rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-3 border-t border-[var(--border)] text-sm text-[var(--muted)]">
                {sortedProducts.length} product(s)
              </div>
            </div>
          )}
        </div>
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
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--muted)]">Enabled Types</th>
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

      {/* Product Modal */}
      {showModal && (
        <ProductModal
          editProduct={editProduct ?? undefined}
          onSaved={fetchProducts}
          onClose={() => { setShowModal(false); setEditProduct(null); }}
        />
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setDeleteConfirm(null)} />
          <div className="relative z-10 w-full max-w-sm p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl">
            <h2 className="text-lg font-bold text-[var(--foreground)] mb-2">Delete Product?</h2>
            <p className="text-sm text-[var(--muted)] mb-5">
              This will delete <strong>{deleteConfirm.plan_code}</strong>. This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--background)]">
                Cancel
              </button>
              <button onClick={handleDelete} disabled={deleting}
                className="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50">
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
