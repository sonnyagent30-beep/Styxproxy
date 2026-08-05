'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { CityPicker } from '@/components/CityPicker';
import { useRouter } from 'next/navigation';
import {
  formatPrice,
  COUNTRIES,
  type CountryInfo,
} from '@/lib/products';
import type { CartItem, CatalogResponse, CatalogTemplate, CatalogVariant, CatalogPlanType } from '@/types';
import { Globe, House, DeviceMobile, HardDrives, ArrowRight, X, ArrowsClockwise } from '@phosphor-icons/react';

// Map catalog plan_type to display icons and labels
function getTypeCardConfig(planType: CatalogPlanType): {
  key: string;
  label: string;
  icon: React.ReactNode;
  description: string;
} {
  switch (planType) {
    case 'isp':
      return {
        key: 'ISP',
        label: 'ISP Proxies',
        icon: <Globe className="w-8 h-8" />,
        description: 'High-speed ISP IPs, ideal for web scraping and automation',
      };
    case 'residential':
      return {
        key: 'RESIDENTIAL',
        label: 'Residential',
        icon: <House className="w-8 h-8" />,
        description: 'Real residential IPs, harder to detect and block',
      };
    case 'mobile':
      return {
        key: 'MOBILE',
        label: 'Mobile 4G',
        icon: <DeviceMobile className="w-8 h-8" />,
        description: 'Mobile carrier IPs, perfect for social media and ad verification',
      };
    case 'datacenter':
      return {
        key: 'DC',
        label: 'Datacenter',
        icon: <HardDrives className="w-8 h-8" />,
        description: 'Fast datacenter proxies for general purpose use',
      };
    default:
      return {
        key: planType.toUpperCase(),
        label: planType,
        icon: <Globe className="w-8 h-8" />,
        description: '',
      };
  }
}

// Extract cheapest price for a template
function getCheapestPrice(template: CatalogTemplate): number | null {
  if (!template.variants || template.variants.length === 0) return null;
  return Math.min(...template.variants.map(v => v.price_ngn));
}

export default function OrderPage() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [addedMessage, setAddedMessage] = useState('');
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [pendingCity, setPendingCity] = useState<{ id: number | null; name: string | null }>({ id: null, name: null });
  const [pendingQtyGb, setPendingQtyGb] = useState<number>(5);

  // Fetch catalog on mount
  useEffect(() => {
    async function fetchCatalog() {
      try {
        const res = await fetch('/api/catalog', { cache: 'no-store' });
        if (!res.ok) {
          throw new Error(`Failed to fetch catalog: ${res.status}`);
        }
        const data: CatalogResponse = await res.json();
        setCatalog(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load catalog');
      } finally {
        setLoading(false);
      }
    }
    fetchCatalog();
  }, []);

  // Load cart from sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem('styxproxy_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) setCart(parsed);
      } catch {}
    }
  }, []);

  // Stale cart fix: verify cart items still exist in catalog
  useEffect(() => {
    if (!catalog || catalog.templates.length === 0) return;
    
    // Build set of valid plan_codes from catalog
    const validPlanCodes = new Set<string>();
    for (const template of catalog.templates) {
      for (const variant of template.variants) {
        validPlanCodes.add(variant.plan_code);
      }
    }
    
    // Remove items whose plan_codes no longer exist
    const validCart = cart.filter(item => validPlanCodes.has(item.plan_code));
    if (validCart.length !== cart.length) {
      setCart(validCart);
      sessionStorage.setItem('styxproxy_cart', JSON.stringify(validCart));
    }
  }, [catalog]);

  const saveCart = useCallback((newCart: CartItem[]) => {
    setCart(newCart);
    sessionStorage.setItem('styxproxy_cart', JSON.stringify(newCart));
  }, []);

  // Build typeCards from catalog
  const typeCards = useMemo(() => {
    if (!catalog || !catalog.templates) return [];
    
    return catalog.templates.map(template => {
      const config = getTypeCardConfig(template.plan_type);
      const cheapestPrice = getCheapestPrice(template);
      const isPerIp = template.plan_type === 'isp' || template.plan_type === 'datacenter';
      
      return {
        ...config,
        price: cheapestPrice !== null 
          ? `From ${formatPrice(cheapestPrice)}${isPerIp ? '/mo' : ''}`
          : 'Check pricing',
        countryCount: template.available_countries?.length || 0,
        hasGeoPlans: template.plan_type === 'isp',
      };
    });
  }, [catalog]);

  // Get current template from active modal
  const currentTemplate = useMemo(() => {
    if (!activeModal || !catalog) return null;
    return catalog.templates.find(t => 
      getTypeCardConfig(t.plan_type).key === activeModal
    ) || null;
  }, [activeModal, catalog]);

  // Get countries for current template
  const templateCountries = useMemo(() => {
    if (!currentTemplate || !currentTemplate.available_countries) return [];
    
    return currentTemplate.available_countries.map(code => {
      const country = COUNTRIES[code.toUpperCase()];
      return {
        code: code.toUpperCase(),
        name: country?.name || code,
        flag: country?.flag || '🌍',
      };
    }).sort((a, b) => a.name.localeCompare(b.name));
  }, [currentTemplate]);

  // Get variants filtered by selected country
  const countryVariants = useMemo(() => {
    if (!currentTemplate || !selectedCountry || !currentTemplate.variants) return [];
    
    return currentTemplate.variants.filter(
      v => v.country.toUpperCase() === selectedCountry.toUpperCase()
    );
  }, [currentTemplate, selectedCountry]);

  const openModal = (key: string) => {
    setActiveModal(key);
    // Set default country to first available
    const template = catalog?.templates.find(t => 
      getTypeCardConfig(t.plan_type).key === key
    );
    const firstCountry = template?.available_countries?.[0]?.toUpperCase();
    setSelectedCountry(firstCountry || null);
    setPendingCity({ id: null, name: null });
    setPendingQtyGb(5);
  };

  const closeModal = () => {
    setActiveModal(null);
    setSelectedCountry(null);
    setPendingCity({ id: null, name: null });
    setPendingQtyGb(5);
  };

  const addToCart = (variant: CatalogVariant, countryCode: string) => {
    const country = COUNTRIES[countryCode.toUpperCase()];
    const isPerGb = currentTemplate?.plan_type === 'residential' || currentTemplate?.plan_type === 'mobile';
    
    // Build cart item name
    const rotationLabel = variant.rotation_mode === 'static' ? 'Static IP' : 'Rotating pool';
    const name = currentTemplate?.plan_type === 'isp'
      ? `${country?.name || countryCode} ISP`
      : `${country?.name || countryCode} · ${rotationLabel}`;

    // Calculate price
    let itemPrice: number;
    let quantityGb: number | undefined;
    let pricePerGb: number | undefined;
    
    if (isPerGb) {
      // Per-GB pricing: price_ngn in cart = variant.price_ngn * quantity_gb
      quantityGb = pendingQtyGb;
      pricePerGb = variant.price_ngn;
      itemPrice = variant.price_ngn * pendingQtyGb;
    } else {
      // Per-IP (ISP/DC): fixed monthly price
      itemPrice = variant.price_ngn;
    }

    const planCode = variant.plan_code;
    const existing = cart.find(i => i.plan_code === planCode);
    
    if (existing) {
      const updated = cart.map(i => {
        if (i.plan_code === planCode) {
          if (isPerGb && typeof i.quantity_gb === 'number') {
            return { ...i, quantity_gb: i.quantity_gb + pendingQtyGb, price_ngn: i.price_ngn + itemPrice };
          }
          return { ...i, quantity: i.quantity + 1 };
        }
        return i;
      });
      saveCart(updated);
    } else {
      const newItem: CartItem = {
        plan_code: planCode,
        name,
        flag: country?.flag || '🌍',
        price_ngn: itemPrice,
        quantity: isPerGb ? 1 : variant.quantity,
        country_code: countryCode.toUpperCase(),
        plan_type: currentTemplate?.plan_type?.toUpperCase() as CartItem['plan_type'],
        quantity_gb: quantityGb,
        city_id: pendingCity.id,
        city_name: pendingCity.name,
        price_per_gb: pricePerGb,
        min_gb: currentTemplate?.min_gb ?? undefined,
        max_gb: currentTemplate?.max_gb ?? undefined,
        gb_tiers: currentTemplate?.gb_tiers ?? undefined,
        supports_city: currentTemplate?.supports_city ?? false,
      };
      saveCart([...cart, newItem]);
    }
    setAddedMessage(`${country?.flag || '🌍'} ${name} added to cart`);
    setTimeout(() => setAddedMessage(''), 2000);
  };

  const cartTotal = cart.reduce((sum, i) => sum + i.price_ngn, 0);
  const cartCount = cart.length;

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    window.location.reload();
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen pt-24 pb-32">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold mb-3">
              Choose Your <span className="gradient-text">Proxy Type</span>
            </h1>
            <p className="text-[var(--muted)]">
              Pick a proxy type, choose your country, and add to cart
            </p>
          </div>
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-[var(--muted)]">
              <ArrowsClockwise className="animate-spin" size={24} />
              <span>Loading catalog...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen pt-24 pb-32">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold mb-3">
              Choose Your <span className="gradient-text">Proxy Type</span>
            </h1>
            <p className="text-[var(--muted)]">
              Pick a proxy type, choose your country, and add to cart
            </p>
          </div>
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <p className="text-red-400">{error}</p>
            <button
              onClick={handleRetry}
              className="px-6 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg transition-all duration-200"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-32">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-3">
            Choose Your <span className="gradient-text">Proxy Type</span>
          </h1>
          <p className="text-[var(--muted)]">
            Pick a proxy type, choose your country, and add to cart
          </p>
        </div>

        {/* Type Cards */}
        <div className="grid sm:grid-cols-2 gap-4">
          {typeCards.map(card => (
            <button
              key={card.key}
              onClick={() => openModal(card.key)}
              className="w-full p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-all text-left group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] group-hover:bg-[var(--primary)]/20 transition-colors">
                  {card.icon}
                </div>
                <ArrowRight className="w-5 h-5 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors" />
              </div>
              <h3 className="text-lg font-bold mb-1">{card.label}</h3>
              <p className="text-sm text-[var(--muted)] mb-3">{card.description}</p>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-[var(--primary)]">{card.price}</span>
                <span className="text-xs text-[var(--muted)]">
                  {card.countryCount} countries
                </span>
              </div>
            </button>
          ))}
        </div>

        {/* Cart Summary Bar */}
        {cart.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 z-40 p-4 bg-[var(--card)]/95 backdrop-blur-sm border-t border-[var(--border)]">
            <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
              <div>
                <span className="font-bold text-[var(--foreground)]">
                  {cartCount} {cartCount === 1 ? 'item' : 'items'}
                </span>
                <span className="text-[var(--muted)] ml-2">{formatPrice(cartTotal)}</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => router.push('/order/checkout')}
                  className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
                >
                  Checkout →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Empty cart nudge */}
        {cart.length === 0 && (
          <div className="mt-16 text-center">
            <p className="text-[var(--muted)] text-sm">Your cart is empty. Pick a proxy type above to get started.</p>
          </div>
        )}

        {/* Added to cart toast */}
        {addedMessage && (
          <div className="fixed bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 bg-[var(--primary)] text-black font-semibold rounded-lg shadow-lg animate-fade-in z-50">
            ✓ {addedMessage}
          </div>
        )}

        {/* =============================================================
            Country + Plan Picker Modal
            ============================================================= */}
        {activeModal && currentTemplate && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={closeModal}
          >
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

            <div
              className="relative w-full max-w-2xl bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden animate-fade-in"
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-[var(--border)]">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h2 className="text-xl font-bold">{getTypeCardConfig(currentTemplate.plan_type).label}</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">
                      Step 1 — pick your country. Step 2 — pick a plan.
                    </p>
                  </div>
                  <button
                    onClick={closeModal}
                    className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Country Grid */}
                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1">
                  {templateCountries.map(c => {
                    const isActive = selectedCountry === c.code;
                    return (
                      <button
                        key={c.code}
                        onClick={() => setSelectedCountry(c.code)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all ${
                          isActive
                            ? 'border-[var(--primary)] bg-[var(--primary)]/15 text-[var(--foreground)] ring-2 ring-[var(--primary)]/30'
                            : 'border-[var(--border)] hover:border-[var(--primary)] text-[var(--muted)] hover:text-[var(--foreground)]'
                        }`}
                      >
                        <span className="text-base leading-none">{c.flag}</span>
                        <span className="font-medium">{c.code}</span>
                      </button>
                    );
                  })}
                </div>
                {selectedCountry && (
                  <p className="text-xs text-[var(--muted)] mt-3">
                    Showing plans for <span className="font-semibold text-[var(--primary)]">
                      {COUNTRIES[selectedCountry]?.flag} {COUNTRIES[selectedCountry]?.name}
                    </span>
                  </p>
                )}

                {/* City picker + GB quantity for residential/mobile */}
                {(() => {
                  const planType = currentTemplate.plan_type;
                  if (planType !== 'residential' && planType !== 'mobile') return null;
                  if (!selectedCountry) return null;

                  const pricePerGb = countryVariants[0]?.price_ngn || 0;
                  const minGb = currentTemplate.min_gb ?? 5;
                  const maxGb = currentTemplate.max_gb ?? 50;
                  const gbTiers = currentTemplate.gb_tiers ?? [minGb, 10, 20, 50];

                  return (
                    <div className="mt-4 p-3 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
                      <CityPicker
                        planType={planType.toUpperCase()}
                        country={selectedCountry}
                        onCountryChange={(c: string) => {
                          setSelectedCountry(c);
                          setPendingCity({ id: null, name: null });
                        }}
                        onCityChange={(city: { id: number; city_name: string } | null) =>
                          setPendingCity({ id: city?.id ?? null, name: city?.city_name ?? null })
                        }
                        selectedCityId={pendingCity.id}
                        showLabels={true}
                        compact={true}
                      />
                      <div className="mt-3">
                        <label className="text-xs text-[var(--muted)] block mb-1">GB amount</label>
                        <div className="flex flex-wrap gap-2">
                          {gbTiers.map((tier: number) => (
                            <button
                              key={tier}
                              onClick={() => setPendingQtyGb(tier)}
                              className={`px-3 py-1 rounded-lg text-sm border transition-colors ${
                                pendingQtyGb === tier
                                  ? 'bg-[var(--primary)] text-black border-[var(--primary)]'
                                  : 'bg-[var(--card)] border-[var(--border)] hover:border-[var(--primary)]'
                              }`}
                            >
                              {tier} GB
                            </button>
                          ))}
                        </div>
                        {pendingQtyGb < minGb && (
                          <p className="text-xs text-amber-400 mt-1">Minimum {minGb} GB</p>
                        )}
                        {pendingQtyGb > maxGb && (
                          <p className="text-xs text-amber-400 mt-1">Maximum {maxGb} GB</p>
                        )}
                        {pricePerGb > 0 && (
                          <p className="text-xs text-[var(--muted)] mt-2">
                            {pendingQtyGb} GB × {formatPrice(pricePerGb)} = {' '}
                            <span className="font-semibold text-[var(--primary)]">
                              {formatPrice(pricePerGb * pendingQtyGb)}
                            </span>
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Plan List */}
              <div className="p-4 max-h-72 overflow-y-auto space-y-2">
                {selectedCountry && (() => {
                  const isIsp = currentTemplate.plan_type === 'isp';

                  // ISP: one plan per country (quantity handled at cart level)
                  if (isIsp) {
                    const countryPlan = countryVariants[0];
                    if (!countryPlan) return null;
                    
                    const cartItem = cart.find(i => i.plan_code === countryPlan.plan_code);
                    const countryInfo = COUNTRIES[selectedCountry];
                    
                    return (
                      <div
                        key={countryPlan.plan_code}
                        className="flex items-center justify-between p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                      >
                        <div>
                          <p className="font-semibold">
                            {countryInfo?.flag} {countryInfo?.name || selectedCountry} ISP
                          </p>
                          <p className="text-sm text-[var(--muted)]">
                            {countryPlan.rotation_mode === 'static' ? 'Static IP' : 'Rotating pool'}
                            {countryPlan.is_active ? ' · In stock' : ' · Out of stock'}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-semibold text-[var(--primary)]">
                            {formatPrice(countryPlan.price_ngn)}/mo
                          </span>
                          <button
                            onClick={() => addToCart(countryPlan, selectedCountry)}
                            disabled={!countryPlan.is_active}
                            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                              countryPlan.is_active
                                ? 'bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black'
                                : 'bg-[var(--border)] text-[var(--muted)] cursor-not-allowed'
                            }`}
                          >
                            {cartItem ? '✓ Added' : '+ Add'}
                          </button>
                        </div>
                      </div>
                    );
                  }

                  // Non-ISP plans (Residential / Mobile / DC)
                  return countryVariants.map(variant => {
                    const cartItem = cart.find(i => i.plan_code === variant.plan_code);
                    const isPerGb = currentTemplate.plan_type === 'residential' || currentTemplate.plan_type === 'mobile';
                    const displayPrice = isPerGb 
                      ? `${formatPrice(variant.price_ngn)}/GB`
                      : `${formatPrice(variant.price_ngn)}/mo`;

                    return (
                      <div
                        key={variant.plan_code}
                        className="flex items-center justify-between p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                      >
                        <div>
                          <p className="font-semibold">
                            {COUNTRIES[selectedCountry]?.flag} {variant.rotation_mode === 'static' ? 'Static' : 'Rotating'}
                          </p>
                          <p className="text-sm text-[var(--muted)]">
                            {variant.quantity} GB{isPerGb ? '' : ' proxy'}
                            {variant.is_active ? ' · In stock' : ' · Out of stock'}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-semibold text-[var(--primary)]">{displayPrice}</span>
                          <button
                            onClick={() => addToCart(variant, selectedCountry)}
                            disabled={!variant.is_active}
                            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                              variant.is_active
                                ? 'bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black'
                                : 'bg-[var(--border)] text-[var(--muted)] cursor-not-allowed'
                            }`}
                          >
                            {cartItem ? '✓ Added' : '+ Add'}
                          </button>
                        </div>
                      </div>
                    );
                  });
                })()}

                {!selectedCountry && (
                  <p className="text-sm text-[var(--muted)] text-center py-6">
                    Pick a country above to see plans.
                  </p>
                )}
              </div>

              {/* Footer */}
              {cart.length > 0 && (
                <div className="p-4 border-t border-[var(--border)]">
                  <button
                    onClick={() => { closeModal(); router.push('/order/checkout'); }}
                    className="w-full py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
                  >
                    Checkout → {formatPrice(cartTotal)}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
