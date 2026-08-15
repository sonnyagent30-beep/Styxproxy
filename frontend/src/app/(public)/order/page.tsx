
/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/set-state-in-effect */

'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  formatPrice,
  COUNTRIES,
  type CountryInfo,
} from '@/lib/products';
import { Flag } from '@/components/ui/Flag';
import { useCartStore } from '@/store/cart-store';
import type { CartItem, CatalogResponse, CatalogTemplate, CatalogVariant, CatalogPlanType } from '@/types';
import { Globe, House, DeviceMobile, HardDrives, Database, ArrowRight, X, ArrowsClockwise, Plus, Minus, Check } from '@phosphor-icons/react';

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
    case 'dc':
      return {
        key: 'DC',
        label: 'Datacenter',
        icon: <Database className="w-8 h-8" />,
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
// DC/ISP: use base_price_per_ip (plan's published rate)
// Residential/Mobile: use cheapest variant price_ngn (volume tier pricing)
function getCheapestPrice(template: CatalogTemplate): number | null {
  if (!template.variants || template.variants.length === 0) return null;
  if (template.plan_type === 'dc' || template.plan_type === 'isp') {
    return template.base_price_per_ip ?? null;
  }
  return Math.min(...template.variants.map(v => v.price_ngn));
}

interface CountrySelection {
  code: string;
  quantity: number;
}

export default function OrderPage() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { items: cart, addItem, removeItem, clearCart, total: cartTotal } = useCartStore();
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [addedMessage, setAddedMessage] = useState('');

  // Residential/Mobile state
  const [selectedCountry, setSelectedCountry] = useState<string>('');
  const [selectedCityId, setSelectedCityId] = useState<number | null>(null);
  const [selectedCityName, setSelectedCityName] = useState<string | null>(null);
  const [selectedGbTier, setSelectedGbTier] = useState<number | null>(null);

  // ISP/DC state
  const [selectedCountries, setSelectedCountries] = useState<CountrySelection[]>([]);

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
      clearCart();
      validCart.forEach(item => addItem(item));
    }
  }, [catalog]);

  // Trigger reveal after catalog loads (cards render async, observer needs a second pass)
  useEffect(() => {
    if (!loading && catalog) {
      setTimeout(() => {
        document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
      }, 100);
    }
  }, [loading, catalog]);

  // Scroll reveal for elements added later
  useEffect(() => {
    const revealEls = document.querySelectorAll('.reveal:not(.visible)');
    if (revealEls.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05, rootMargin: '0px 0px -10% 0px' }
    );
    revealEls.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [loading, catalog]);


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
        supportsCity: template.supports_city,
        planType: template.plan_type,
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
        countryCode: code.toUpperCase(),
      };
    }).sort((a, b) => a.name.localeCompare(b.name));
  }, [currentTemplate]);

  // Get cities for selected country (for res/mobile)
  const availableCities = useMemo(() => {
    if (!currentTemplate || !selectedCountry || !currentTemplate.cities) return [];
    return currentTemplate.cities[selectedCountry] || [];
  }, [currentTemplate, selectedCountry]);

  // Get GB tiers for current template
  const gbTiers = useMemo(() => {
    if (!currentTemplate) return [];
    return currentTemplate.gb_tiers || [];
  }, [currentTemplate]);

  // Get base price per GB for current template/country
  // For Res/Mobile: price_ngn is TOTAL for variant.quantity GB, so divide to get per-GB
  // Falls back to template base_price_per_gb when no country selected
  const pricePerGb = useMemo(() => {
    if (!currentTemplate) return 0;
    if (!selectedCountry || !currentTemplate.variants) {
      // No country selected — use template's base price per GB
      return (currentTemplate as any).base_price_per_gb || 0;
    }
    const variant = currentTemplate.variants.find(
      v => v.country.toUpperCase() === selectedCountry.toUpperCase()
    );
    if (!variant || variant.quantity === 0) return 0;
    // price_ngn is total for variant.quantity GB — divide to get true per-GB
    return variant.price_ngn / variant.quantity;
  }, [currentTemplate, selectedCountry]);

  // Check if current template supports city (residential/mobile)
  const supportsCity = currentTemplate?.supports_city ?? false;

  // Open modal and reset state
  const openModal = (key: string) => {
    setActiveModal(key);
    // Reset state
    setSelectedCountry('');
    setSelectedCityId(null);
    setSelectedCityName(null);
    setSelectedGbTier(null);
    setSelectedCountries([]);
  };

  const closeModal = () => {
    setActiveModal(null);
    setSelectedCountry('');
    setSelectedCityId(null);
    setSelectedCityName(null);
    setSelectedGbTier(null);
    setSelectedCountries([]);
  };

  // Toggle country selection for ISP/DC
  const toggleCountryForIsp = (code: string) => {
    const existing = selectedCountries.find(c => c.code === code);
    if (existing) {
      setSelectedCountries(selectedCountries.filter(c => c.code !== code));
    } else {
      setSelectedCountries([...selectedCountries, { code, quantity: 1 }]);
    }
  };

  // Update quantity for ISP/DC country
  const updateCountryQuantity = (code: string, quantity: number) => {
    setSelectedCountries(
      selectedCountries.map(c => 
        c.code === code ? { ...c, quantity: Math.max(1, quantity) } : c
      )
    );
  };


  // Add to cart for Residential/Mobile
  // Country is OPTIONAL — user can pick GB and checkout without country
  const addResidentialToCart = () => {
    if (!currentTemplate || !selectedGbTier) return;

    const country = selectedCountry ? COUNTRIES[selectedCountry.toUpperCase()] : null;
    // Build plan code: use COUNTRY_CODE if selected, else GENERIC
    const planCode = selectedCountry
      ? `${currentTemplate.plan_type}-${selectedCountry.toUpperCase()}-${selectedGbTier}`
      : `${currentTemplate.plan_type}-GENERIC-${selectedGbTier}`;

    // Find variant for price if country selected
    const variant = selectedCountry
      ? currentTemplate.variants?.find(
          v => v.country.toUpperCase() === selectedCountry.toUpperCase()
        )
      : null;

    // Calculate per-GB: use variant if found (variant.price / variant.qty), else template base_price_per_gb
    const effectivePricePerGb = variant && variant.quantity > 0
      ? variant.price_ngn / variant.quantity
      : (currentTemplate as any).base_price_per_gb || 0;

    const itemPrice = effectivePricePerGb * selectedGbTier;

    const locationLabel = selectedCountry
      ? `${country?.name || selectedCountry}`
      : 'Any location';
    const name = `${locationLabel}, ${selectedGbTier} GB`;

    const existing = cart.find(i => i.plan_code === planCode);

    if (existing) {
      const updated = cart.map(i => {
        if (i.plan_code === planCode) {
          return {
            ...i,
            quantity_gb: (i.quantity_gb || 0) + selectedGbTier,
            price_ngn: i.price_ngn + itemPrice,
          };
        }
        return i;
      });
      clearCart();
      updated.forEach(item => addItem(item));
    } else {
      const newItem: CartItem = {
        plan_code: planCode,
        name,
        flag: country?.flag || '',
        price_ngn: itemPrice,
        quantity: 1,
        country_code: selectedCountry ? selectedCountry.toUpperCase() : 'GENERIC',
        plan_type: currentTemplate.plan_type.toUpperCase() as CartItem['plan_type'],
        quantity_gb: selectedGbTier,
        city_id: selectedCityId,
        city_name: selectedCityName,
        price_per_gb: effectivePricePerGb,
        min_gb: currentTemplate.min_gb ?? undefined,
        max_gb: currentTemplate.max_gb ?? undefined,
        gb_tiers: gbTiers,
        supports_city: supportsCity,
      };
      addItem(newItem);
    }
    setAddedMessage(`${country?.name || selectedCountry?.toUpperCase() || ''} added to cart`);
    setTimeout(() => setAddedMessage(''), 2000);
  };

  // Add to cart for ISP/DC
  const addIspDcToCart = () => {
    if (!currentTemplate || selectedCountries.length === 0) return;

    const newItems: CartItem[] = selectedCountries.map(selection => {
      const country = COUNTRIES[selection.code.toUpperCase()];
      
      // Find the variant for this country
      const variant = currentTemplate.variants?.find(
        v => v.country.toUpperCase() === selection.code.toUpperCase()
      );

      const itemPrice = (variant?.price_ngn || 0) * selection.quantity;
      const planCode = `${currentTemplate.plan_type}-${selection.code.toUpperCase()}-${selection.quantity}`;

      const name = `${country?.name || selection.code} x${selection.quantity} IPs`;

      return {
        plan_code: planCode,
        name,
        flag: country?.flag || '🌍',
        price_ngn: itemPrice,
        quantity: selection.quantity,
        country_code: selection.code.toUpperCase(),
        plan_type: currentTemplate.plan_type.toUpperCase() as CartItem['plan_type'],
        quantity_gb: undefined,
        city_id: undefined,
        city_name: undefined,
        price_per_gb: undefined,
        supports_city: false,
      };
    });

    // Add new items, avoiding duplicates by updating existing
    const updatedCart = [...cart];
    for (const newItem of newItems) {
      const existingIndex = updatedCart.findIndex(i => 
        i.plan_type === newItem.plan_type && 
        i.country_code === newItem.country_code
      );
      if (existingIndex >= 0) {
        updatedCart[existingIndex] = {
          ...updatedCart[existingIndex],
          quantity: updatedCart[existingIndex].quantity + newItem.quantity,
          price_ngn: updatedCart[existingIndex].price_ngn + newItem.price_ngn,
        };
      } else {
        updatedCart.push(newItem);
      }
    }
    
    clearCart();
    updatedCart.forEach(item => addItem(item));
    const count = selectedCountries.length;
    setAddedMessage(`${count} ${count === 1 ? 'country' : 'countries'} added to cart`);
    setTimeout(() => setAddedMessage(''), 2000);
  };

  
  const cartCount = cart.length;

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    window.location.reload();
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen pb-32">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-center justify-center py-32">
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
      <div className="min-h-screen pb-32">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex flex-col items-center justify-center py-32 gap-4">
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
    <div className="min-h-screen pb-32">
      {/* Hero — full width, outside the constrained container */}
      <div className="relative overflow-hidden pt-24 pb-12">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="hero-orb-1" />
        <div className="hero-orb-2" />
        <div className="hero-orb-3" />

        <div className="relative text-center max-w-3xl mx-auto px-4">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6 mx-auto">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
            <span className="text-xs font-bold uppercase tracking-widest text-[var(--primary)]">Order Proxies</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight mb-4">
            Get Your <span className="text-[var(--primary)]">Proxies</span> Now
          </h1>
          <p className="text-base text-[var(--muted)] max-w-xl mx-auto">
            Pick a proxy type, choose your country, checkout in seconds. No signup required.
          </p>

          {/* Scroll indicator */}
          <div className="flex flex-col items-center gap-2 pt-8">
            <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
            <div className="w-px h-8 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
          </div>
        </div>
      </div>

      {/* Rest of page — constrained */}
      <div className="max-w-4xl mx-auto px-4">
        {/* Type Cards */}
        <div className="grid sm:grid-cols-2 gap-4 reveal">
          {typeCards.map(card => (
            <button
              key={card.key}
              onClick={() => openModal(card.key)}
              className="w-full p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-all text-left group card-depth"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] group-hover:bg-[var(--primary)]/20 transition-colors">
                  {card.icon}
                </div>
                <ArrowRight className="w-5 h-5 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors" />
              </div>
              <h3 className="text-base font-bold mb-1">{card.label}</h3>
              <p className="text-xs text-[var(--muted)] mb-3">{card.description}</p>
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
                <span className="text-[var(--muted)] ml-2">{formatPrice(cartTotal())}</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => router.push('/order/checkout')}
                  className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
                >
                  Checkout
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
            <Check className="inline w-4 h-4 mr-1" />
            {addedMessage}
          </div>
        )}

        {/* =============================================================
            Modal for Residential & Mobile (supports_city = true)
            ============================================================= */}
        {activeModal && currentTemplate && supportsCity && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={closeModal}
          >
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

            <div
              className="relative w-full max-w-lg bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden animate-fade-in"
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-[var(--border)]">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold">{getTypeCardConfig(currentTemplate.plan_type).label}</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">
                      Select country, city, and GB amount
                    </p>
                  </div>
                  <button
                    onClick={closeModal}
                    className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Step 3: GB Tier Buttons — shown BEFORE country (country is optional) */}
                {gbTiers.length > 0 && (
                  <div className="mb-4">
                    <label className="text-sm font-medium mb-2 block">GB Amount</label>
                    <div className="flex flex-wrap gap-2">
                      {gbTiers.map(tier => (
                        <button
                          key={tier}
                          onClick={() => setSelectedGbTier(tier)}
                          className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                            selectedGbTier === tier
                              ? 'bg-[var(--primary)] text-black border-[var(--primary)]'
                              : 'bg-[var(--background)] border-[var(--border)] hover:border-[var(--primary)]'
                          }`}
                        >
                          {tier} GB
                        </button>
                      ))}
                    </div>
                    {selectedGbTier && pricePerGb > 0 && (
                      <p className="text-sm text-[var(--muted)] mt-2">
                        {selectedGbTier} GB @ {formatPrice(pricePerGb)}/GB = {' '}
                        <span className="font-semibold text-[var(--primary)]">
                          {formatPrice(pricePerGb * selectedGbTier)}
                        </span>
                      </p>
                    )}
                  </div>
                )}

                {/* Step 4: Country Dropdown (optional) */}
                <div className="mb-4">
                  <label className="text-sm font-medium mb-2 block">
                    Country <span className="text-[var(--muted)]">(optional)</span>
                  </label>
                  <select
                    value={selectedCountry}
                    onChange={(e) => {
                      setSelectedCountry(e.target.value);
                      setSelectedCityId(null);
                      setSelectedCityName(null);
                    }}
                    className="w-full px-3 py-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                  >
                    <option value="">Select a country</option>
                    {templateCountries.map(c => (
                      <option key={c.code} value={c.code}>
                        {c.name} ({c.code})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Step 3: City Dropdown (optional) */}
                {selectedCountry && availableCities.length > 0 && (
                  <div className="mb-4">
                    <label className="text-sm font-medium mb-2 block">City (optional)</label>
                    <select
                      value={selectedCityId ?? ''}
                      onChange={(e) => {
                        const cityId = e.target.value ? parseInt(e.target.value) : null;
                        setSelectedCityId(cityId);
                        const city = availableCities.find(c => c.id === cityId);
                        setSelectedCityName(city?.city_name || null);
                      }}
                      className="w-full px-3 py-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                    >
                      <option value="">Random (any city)</option>
                      {availableCities.map(city => (
                        <option key={city.id} value={city.id}>
                          {city.city_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

              </div>

              {/* Footer: Add to Cart */}
              <div className="p-4 border-t border-[var(--border)]">
                <button
                  onClick={addResidentialToCart}
                  disabled={!selectedGbTier}
                  className={`w-full py-3 font-semibold rounded-xl transition-colors ${
                    selectedGbTier
                      ? 'bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black'
                      : 'bg-[var(--border)] text-[var(--muted)] cursor-not-allowed'
                  }`}
                >
                  {!selectedGbTier ? 'Select a GB amount' : 'Add to Cart'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* =============================================================
            Modal for ISP & DC (supports_city = false)
            ============================================================= */}
        {activeModal && currentTemplate && !supportsCity && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={closeModal}
          >
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

            <div
              className="relative w-full max-w-2xl bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden animate-fade-in max-h-[90vh] flex flex-col"
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-[var(--border)]">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold">{getTypeCardConfig(currentTemplate.plan_type).label}</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">
                      Select countries and quantity per country
                    </p>
                  </div>
                  <button
                    onClick={closeModal}
                    className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Step 2: Country Flag Grid */}
                <div className="mb-4">
                  <label className="text-sm font-medium mb-2 block">Countries (click to select)</label>
                  <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1">
                    {templateCountries.map(c => {
                      const isSelected = selectedCountries.some(sc => sc.code === c.code);
                      return (
                        <button
                          key={c.code}
                          onClick={() => toggleCountryForIsp(c.code)}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all ${
                            isSelected
                              ? 'border-[var(--primary)] bg-[var(--primary)]/15 text-[var(--foreground)] ring-2 ring-[var(--primary)]/30'
                              : 'border-[var(--border)] hover:border-[var(--primary)] text-[var(--muted)] hover:text-[var(--foreground)]'
                          }`}
                        >
                          <Flag countryCode={c.code} size={18} />
                          <span className="font-medium">{c.name}</span>
                          <span className="text-[var(--muted)] text-xs">({c.code})</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Selected Countries with Quantity */}
              {selectedCountries.length > 0 && (
                <div className="p-4 border-b border-[var(--border)] max-h-64 overflow-y-auto space-y-3">
                  <label className="text-sm font-medium mb-2 block">Selected Countries</label>
                  {selectedCountries.map(selection => {
                    const country = COUNTRIES[selection.code];
                    const variant = currentTemplate.variants?.find(
                      v => v.country.toUpperCase() === selection.code.toUpperCase()
                    );
                    const pricePerIp = variant?.price_ngn || 0;
                    const totalPrice = pricePerIp * selection.quantity;

                    return (
                      <div
                        key={selection.code}
                        className="flex items-center gap-3 p-3 rounded-xl bg-[var(--card)] border border-[var(--border)] card-depth"
                      >
                        <Flag countryCode={selection.code} size={32} />
                        <div className="flex-1">
                          <p className="font-semibold">{country?.name || selection.code}</p>
                          <p className="text-xs text-[var(--muted)]">
                            {formatPrice(pricePerIp)}/mo each
                          </p>
                        </div>
                        
                        {/* Quantity Input */}
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => updateCountryQuantity(selection.code, selection.quantity - 1)}
                            disabled={selection.quantity <= 1}
                            className="w-8 h-8 rounded-lg border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Minus className="w-4 h-4" />
                          </button>
                          <input
                            type="number"
                            min="1"
                            value={selection.quantity}
                            onChange={(e) => updateCountryQuantity(selection.code, parseInt(e.target.value) || 1)}
                            className="w-16 px-2 py-1 text-center rounded-lg bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                          />
                          <button
                            onClick={() => updateCountryQuantity(selection.code, selection.quantity + 1)}
                            className="w-8 h-8 rounded-lg border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)]"
                          >
                            <Plus className="w-4 h-4" />
                          </button>
                        </div>

                        <span className="text-sm font-semibold text-[var(--primary)] min-w-[80px] text-right">
                          {formatPrice(totalPrice)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Footer: Add to Cart */}
              <div className="p-4 border-t border-[var(--border)]">
                <button
                  onClick={addIspDcToCart}
                  disabled={selectedCountries.length === 0}
                  className={`w-full py-3 font-semibold rounded-xl transition-colors ${
                    selectedCountries.length > 0
                      ? 'bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black'
                      : 'bg-[var(--border)] text-[var(--muted)] cursor-not-allowed'
                  }`}
                >
                  Add to Cart
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
